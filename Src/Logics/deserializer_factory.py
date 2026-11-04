import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import ClassVar

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException, OperationException
from Src.Logics.ingredient_deserializer import IngredientDeserializer
from Src.Logics.nomenclature_deserializer import NomenclatureDeserializer
from Src.Logics.nomenclature_group_deserializer import NomenclatureGroupDeserializer
from Src.Logics.range_deserializer import RangeDeserializer
from Src.Logics.recipe_deserializer import RecipeDeserializer
from Src.Logics.warehouse_deserializer import WarehouseDeserializer
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.warehouse_model import WarehouseModel


class DeserializerFactory:
    """Фабрика десериализаторов: по целевому типу выбирает десериализатор и рекурсивно собирает модель.

    Клиент вызывает только ``deserialize(target_type, data)``. Это обратная сторона ``ConverterFactory``.

    Проектные решения:

    - Десериализатор выбирается по **целевому типу** (что ждёт конструктор), а не по типу значения, как у
      конвертеров: у значения из JSON своего типа нет. Выбор по точному типу, без обхода MRO: нужна именно та
      модель, которую запросили.
    - Сопоставление «тип модели — класс десериализатора» лежит в ``_deserializers``, как в ``ReportFactory``.
      Новая модель подключается строкой в нём.
    - Рекурсия идёт через функцию: фабрика передаёт десериализаторам ``_resolve``, а они вызывают её
      для вложенных моделей. Десериализаторы не зависят от класса фабрики, цикла импортов нет.
    - Все десериализаторы одной загрузки делят один кэш собранных моделей по идентификатору. Поэтому единица
      измерения, вложенная полным словарём в каждую номенклатуру, собирается один раз, а не копируется.
    - Кэш живёт только на время ``deserialize``: следующая загрузка начинается с чистого, и данные нового файла
      не подменяются объектами прежнего. Из-за кэша фабрика хранит состояние и не годится для параллельных вызовов.
    - Если данные состоят из нескольких частей (коллекции хранилища), а модели должны быть общими между ними,
      части загружаются в одной сессии: ``with factory.session(): ...``. Внутри сессии кэш не сбрасывается между
      вызовами ``deserialize`` и очищается при выходе из неё, в том числе после ошибки.
    """

    # Сопоставление типа модели и класса её десериализатора
    _deserializers: ClassVar[dict[type, type[AbstractDeserializer]]] = {
        RangeModel: RangeDeserializer,
        NomenclatureGroupModel: NomenclatureGroupDeserializer,
        NomenclatureModel: NomenclatureDeserializer,
        WarehouseModel: WarehouseDeserializer,
        IngredientModel: IngredientDeserializer,
        RecipeModel: RecipeDeserializer,
    }

    # Собранные модели по идентификатору, общий для всех десериализаторов одной загрузки
    _cache: dict[uuid.UUID, BaseEntity]
    # Открыта ли сессия: в ней кэш не сбрасывается после каждого deserialize
    _in_session: bool

    def __init__(self) -> None:
        """Инициализирует фабрику с пустым кэшем."""
        self._cache = {}
        self._in_session = False

    @contextmanager
    def session(self) -> Generator[None]:
        """Открывает сессию загрузки: модели, собранные в ней, общие для всех вызовов ``deserialize``.

        Применяется, когда одна модель встречается в разных частях данных. Например, единица измерения
        есть и в коллекции единиц, и внутри каждой номенклатуры, и это должен быть один объект.
        Без сессии каждый ``deserialize`` собирал бы свои копии.

        При выходе из сессии кэш очищается, в том числе если внутри возникла ошибка.

        :raises OperationException: Если сессия уже открыта: вложенная очистила бы кэш внешней раньше времени.
        """
        if self._in_session:
            raise OperationException("Сессия десериализации уже открыта")

        self._in_session = True
        try:
            yield
        finally:
            self._in_session = False
            self._cache.clear()

    def create(self, target_type: type) -> AbstractDeserializer:
        """Создаёт десериализатор для указанного типа модели.

        Десериализатор получает функцию рекурсии и общий кэш фабрики.

        :param target_type: Тип модели, которую нужно собрать.
        :return: Новый десериализатор этой модели.
        :raises ArgumentsException: Если значение не тип или для типа нет десериализатора.
        """
        target_type = CommonValidator.validate_instance(target_type, type, "target_type", "Ожидается тип модели")
        deserializer = self._deserializers.get(target_type)
        if deserializer is None:
            raise ArgumentsException("target_type", f"Нет десериализатора для {target_type.__name__}")

        return deserializer(self._resolve, self._cache)

    def deserialize[T](self, target_type: type[T], data: object) -> T:
        """Превращает данные из JSON в модель заданного типа, вложенные модели собирает рекурсивно.

        Это точка входа для клиента. Десериализаторы её не вызывают, для вложенных моделей у них
        есть ``_resolve``: иначе кэш сбросился бы посреди загрузки. Вне сессии кэш очищается после вызова,
        в сессии (см. ``session``) — при выходе из неё.

        :param target_type: Тип модели, которую нужно собрать.
        :param data: Словарь полей модели, как его записал ``ConverterFactory``.
        :return: Собранная модель.
        :raises ArgumentsException: Если нет десериализатора для типа, данные некорректны
            или десериализатор вернул модель другого типа.
        :raises OperationException: Если в данных есть ссылка на модель, которой нет в данных.
        """
        try:
            model = self._resolve(target_type, data)
            return CommonValidator.validate_instance(
                model, target_type, "target_type", f"Десериализатор вернул не {target_type.__name__}"
            )
        finally:
            if not self._in_session:
                self._cache.clear()

    def _resolve(self, target_type: type, data: object) -> object:
        """Собирает модель заданного типа, кэш не сбрасывает: вызывается рекурсивно из десериализаторов.

        :param target_type: Тип модели, которую нужно собрать.
        :param data: Данные модели.
        :return: Собранная модель.
        :raises ArgumentsException: Если нет десериализатора для типа или данные некорректны.
        :raises OperationException: Если в данных есть ссылка на неизвестную модель.
        """
        # Рекурсия: десериализатор в _build снова вызовет эту функцию для вложенных моделей
        return self.create(target_type).deserialize(data)
