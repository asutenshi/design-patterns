import uuid
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from types import NoneType

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException, OperationException
from Src.Logics.basic_deserializer import BasicDeserializer
from Src.Logics.list_deserializer import ListDeserializer
from Src.Logics.model_deserializer import ModelDeserializer


class DeserializerFactory:
    """Фабрика десериализаторов: превращает данные из JSON обратно в модели, вложенные — рекурсивно.

    Клиент вызывает ``deserialize(data)`` или, если ждёт модель определённого типа, ``deserialize_as``.
    Это обратная сторона ``ConverterFactory``.

    Проектные решения:

    - Десериализатор выбирается по **виду значения**, как конвертер у ``ConverterFactory``: словарь — модель,
      список — список, строка, число, bool и None — простое значение. Какую модель собирать, записано
      в самих данных (``model_type``), поэтому фабрика не знает ни одной конкретной модели. Новая модель
      подключается только своим ``AbstractModel.from_dict``.
    - Модель по ``model_type`` ищется в реестре наследников ``AbstractModel``. В реестре только классы,
      чьи модули уже импортированы. Модели хранилища импортирует ``StorageManager``.
    - Рекурсия идёт через функцию: фабрика передаёт десериализаторам ``_resolve``, а они вызывают её
      для вложенных значений. Десериализаторы не зависят от класса фабрики, цикла импортов нет.
    - Собранные модели лежат в кэше по идентификатору, общем для всех десериализаторов одной загрузки.
      Поэтому единица измерения, вложенная полным словарём в каждую номенклатуру, собирается один раз,
      а не копируется. Кэш живёт только на время ``deserialize``: следующая загрузка начинается с чистого.
      Из-за кэша фабрика хранит состояние и не годится для параллельных вызовов.
    - Если данные состоят из нескольких частей (коллекции хранилища), а модели должны быть общими между ними,
      части загружаются в одной сессии: ``with factory.session(): ...``. Внутри сессии кэш не сбрасывается между
      вызовами ``deserialize`` и очищается при выходе из неё, в том числе после ошибки.
    """

    # Сопоставление вида значения из JSON и его десериализатора
    _deserializers: dict[type, AbstractDeserializer]
    # Собранные модели по идентификатору, общий для всех десериализаторов одной загрузки
    _cache: dict[uuid.UUID, BaseEntity]
    # Идентификаторы моделей, которые собираются сейчас: по ним десериализатор моделей узнаёт цикл
    _in_progress: set[uuid.UUID]
    # Открыта ли сессия: в ней кэш не сбрасывается после каждого deserialize
    _in_session: bool

    def __init__(self) -> None:
        """Инициализирует фабрику с пустым кэшем и её десериализаторы."""
        self._cache = {}
        self._in_progress = set()
        self._in_session = False
        basic = BasicDeserializer()
        self._deserializers = {
            str: basic,
            int: basic,
            float: basic,
            NoneType: basic,
            list: ListDeserializer(self._resolve),
            dict: ModelDeserializer(self._resolve, self._cache, self._in_progress),
        }

    @contextmanager
    def session(self, known: Iterable[BaseEntity] = ()) -> Generator[None]:
        """Открывает сессию загрузки: модели, собранные в ней, общие для всех вызовов ``deserialize``.

        Применяется, когда одна модель встречается в разных частях данных. Например, единица измерения
        есть и в коллекции единиц, и внутри каждой номенклатуры, и это должен быть один объект.
        Без сессии каждый ``deserialize`` собирал бы свои копии.

        Известные сущности кладутся в кэш сразу: ссылка ``{"id": ...}`` на них разворачивается в тот же объект.
        Так данные из API ссылаются на сущности хранилища, которых в самих данных нет. Если в данных есть
        словарь с идентификатором известной сущности, возвращается она сама, остальные поля словаря игнорируются.

        При выходе из сессии кэш очищается, в том числе если внутри возникла ошибка.

        :param known: Сущности, которые уже существуют и на которые могут ссылаться данные.
        :raises OperationException: Если сессия уже открыта: вложенная очистила бы кэш внешней раньше времени.
        """
        if self._in_session:
            raise OperationException("Сессия десериализации уже открыта")

        self._in_session = True
        self._cache.update({entity.id: entity for entity in known})
        try:
            yield
        finally:
            self._in_session = False
            self._cache.clear()

    def create(self, data: object) -> AbstractDeserializer:
        """Выбирает десериализатор по виду значения.

        Типы проверяются от класса значения к его базовым классам: ``bool`` находится через ``int``.

        :param data: Значение, как его вернул ``json.load``.
        :return: Десериализатор этого значения.
        :raises ArgumentsException: Если значение не из тех, что бывают в JSON (например, кортеж или множество).
        """
        for klass in type(data).__mro__:
            deserializer = self._deserializers.get(klass)
            if deserializer is not None:
                return deserializer
        raise ArgumentsException("data", f"Значение не из JSON: {type(data).__name__}")

    def deserialize(self, data: object) -> object:
        """Превращает данные из JSON в объекты, вложенные модели собирает рекурсивно.

        Это точка входа для клиента. Десериализаторы её не вызывают, для вложенных значений у них
        есть ``_resolve``: иначе кэш сбросился бы посреди загрузки. Вне сессии кэш очищается после вызова,
        в сессии (см. ``session``) — при выходе из неё.

        :param data: Данные, как их записал ``ConverterFactory`` и прочитал ``json.load``.
        :return: Модель для словаря модели, список для списка, простое значение для простого значения.
        :raises ArgumentsException: Если значение не из JSON, у словаря нет ``model_type``, тип модели
            неизвестен или модель не собралась.
        :raises OperationException: Если в данных ссылка на модель, которой нет в данных.
        """
        try:
            return self._resolve(data)
        finally:
            if not self._in_session:
                self._cache.clear()

    def deserialize_as[T](self, target_type: type[T], data: object) -> T:
        """Превращает данные из JSON в объект и проверяет, что получен ожидаемый тип.

        Тип не выбирает модель, её выбирают данные (``model_type``). Он только проверяет результат:
        например, что в коллекции единиц измерения лежат именно единицы.

        :param target_type: Ожидаемый тип результата.
        :param data: Данные, как их записал ``ConverterFactory`` и прочитал ``json.load``.
        :return: Объект ожидаемого типа.
        :raises ArgumentsException: Если данные некорректны (см. ``deserialize``) или собран объект другого типа.
        :raises OperationException: Если в данных ссылка на модель, которой нет в данных.
        """
        target_type = CommonValidator.validate_instance(target_type, type, "target_type", "Ожидается тип")
        return CommonValidator.validate_instance(
            self.deserialize(data), target_type, "data", f"Ожидается {target_type.__name__}"
        )

    def _resolve(self, data: object) -> object:
        """Собирает объект из значения, кэш не сбрасывает: вызывается рекурсивно из десериализаторов.

        :param data: Значение из JSON.
        :return: Собранный объект.
        :raises ArgumentsException: Если значение не из JSON или модель не собралась.
        :raises OperationException: Если в данных ссылка на неизвестную модель.
        """
        # Рекурсия: десериализатор снова вызовет эту функцию для вложенных значений
        return self.create(data).deserialize(data)
