import uuid
from collections.abc import Callable
from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.abstract_model import AbstractModel
from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException, OperationException

# Ключ, под которым в данных хранится идентификатор модели
_ID_KEY = "id"


class ModelDeserializer(AbstractDeserializer):
    """Десериализатор моделей: словарь из JSON превращается в модель того типа, что записан в ``model_type``.

    Десериализатор не знает ни одной конкретной модели. Класс он находит по ``model_type``
    (``AbstractModel.resolve_type``), все значения полей собирает рекурсивно функцией фабрики, а модель
    создаёт её же фабричным методом ``from_dict``. Модель получает уже собранные вложенные модели.

    Проектные решения:

    - Одна модель в JSON встречается много раз: единица измерения внутри каждой номенклатуры. Собранные
      модели лежат в кэше по идентификатору, повторная встреча возвращает тот же объект, а не его копию.
      Кэш общий для всей загрузки, им владеет фабрика.
    - Конструкторы моделей не принимают идентификатор, поэтому он выставляется после ``from_dict``.
      У части моделей идентификатора нет (ингредиент), такие модели в кэш не попадают.
    - Ссылка ``{"id": ...}`` разворачивается из кэша. Если модель с этим идентификатором ещё собирается
      (она выше по вложенности), это цикл, и вместо модели передаётся ``None``. В домене цикл один:
      базовая единица ссылается сама на себя, а ``RangeModel`` понимает ``base=None`` как «я базовая».
      Сериализатор пишет такую ссылку только для циклов, поэтому порядок моделей в данных на результат
      не влияет. Ссылка на модель, которой нет ни в кэше, ни среди собираемых, — ошибка.
    """

    # Функция фабрики, превращающая значение из JSON в объект
    _resolve: Callable[[object], object]
    # Собранные модели по идентификатору, общий для всей загрузки
    _cache: dict[uuid.UUID, BaseEntity]
    # Идентификаторы моделей, которые собираются сейчас: путь от корня до текущей модели
    _in_progress: set[uuid.UUID]

    def __init__(
        self,
        resolve: Callable[[object], object],
        cache: dict[uuid.UUID, BaseEntity],
        in_progress: set[uuid.UUID],
    ) -> None:
        """Инициализирует десериализатор.

        :param resolve: Функция, превращающая значение из JSON в объект.
        :param cache: Кэш собранных моделей по идентификатору, общий для всей загрузки.
        :param in_progress: Идентификаторы моделей, которые собираются сейчас, общие для всей загрузки.
        :raises ArgumentsException: Если ``resolve`` нельзя вызвать, ``cache`` не словарь или ``in_progress`` не множество.
        """
        self._resolve = CommonValidator.validate_callable(resolve, "resolve", "Ожидается функция десериализации")
        self._cache = cast(
            dict[uuid.UUID, BaseEntity], CommonValidator.validate_instance(cache, dict, "cache", "Ожидается словарь")
        )
        self._in_progress = cast(
            set[uuid.UUID],
            CommonValidator.validate_instance(in_progress, set, "in_progress", "Ожидается множество"),
        )

    @override
    def deserialize(self, data: object) -> object:
        """Превращает словарь из JSON в модель, повторную встречу той же модели возвращает из кэша.

        :param data: Словарь полей модели с ``model_type`` или ссылка ``{"id": ...}``.
        :return: Модель. Одному идентификатору соответствует один и тот же объект. Для ссылки на модель,
            которая сейчас собирается (цикл), — None.
        :raises ArgumentsException: Если данные не словарь, в них нет ``model_type``, тип неизвестен,
            идентификатор некорректен или модель не собралась.
        :raises OperationException: Если ссылка указывает на модель, которой нет в данных.
        """
        fields = CommonValidator.validate_dict(data, "data")
        entity_id = self._read_id(fields)

        if entity_id is not None and entity_id in self._cache:
            return self._cache[entity_id]
        if entity_id is not None and fields.keys() == {_ID_KEY}:
            # Ссылка на модель, которая собирается выше по вложенности, замыкает цикл
            if entity_id in self._in_progress:
                return None
            raise OperationException(f"Ссылка на неизвестный объект: {entity_id}")

        model_class = AbstractModel.resolve_type(CommonValidator.validate_field(fields, AbstractModel.TYPE_FIELD))
        model = self._build(model_class, fields, entity_id)
        if entity_id is not None:
            entity = CommonValidator.validate_instance(model, BaseEntity, _ID_KEY, "Идентификатор есть только у сущности")
            entity.id = entity_id
            self._cache[entity_id] = entity
        return model

    def _build(
        self, model_class: type[AbstractModel], fields: dict[str, object], entity_id: uuid.UUID | None
    ) -> AbstractModel:
        """Собирает значения полей рекурсивно и создаёт модель её фабричным методом.

        Пока собираются вложенные значения, идентификатор модели числится среди собираемых:
        ссылка на неё ниже по вложенности — цикл.

        :param model_class: Класс модели.
        :param fields: Словарь полей модели из JSON.
        :param entity_id: Идентификатор модели или None, если его нет.
        :return: Новая модель без выставленного идентификатора.
        :raises ArgumentsException: Если вложенное значение или сама модель не собрались.
        :raises OperationException: Если в данных ссылка на модель, которой нет в данных.
        """
        if entity_id is not None:
            self._in_progress.add(entity_id)
        try:
            # Рекурсия: функция фабрики выберет десериализатор для значения каждого поля
            values = {
                key: self._resolve(value)
                for key, value in fields.items()
                if key not in (_ID_KEY, AbstractModel.TYPE_FIELD)
            }
            return model_class.from_dict(values)
        finally:
            if entity_id is not None:
                self._in_progress.discard(entity_id)

    @staticmethod
    def _read_id(data: dict[str, object]) -> uuid.UUID | None:
        """Читает идентификатор из данных.

        :param data: Словарь полей модели.
        :return: Идентификатор или None, если ключа ``id`` в данных нет.
        :raises ArgumentsException: Если идентификатор не строка с UUID.
        """
        if _ID_KEY not in data:
            return None
        raw = data[_ID_KEY]
        if not isinstance(raw, str):
            raise ArgumentsException(_ID_KEY, "Идентификатор должен быть строкой")
        try:
            return uuid.UUID(raw)
        except ValueError as ex:
            raise ArgumentsException(_ID_KEY, f"Некорректный идентификатор: {raw}") from ex
