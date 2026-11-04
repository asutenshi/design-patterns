import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import cast

from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException, OperationException

# Ключ, по которому в данных хранится идентификатор модели
_ID_KEY = "id"


class AbstractDeserializer(ABC):
    """Абстрактный десериализатор: превращает словарь из JSON в модель.

    У каждой модели свой наследник, который знает её конструктор и поля. Десериализатор выбирает по целевому
    типу фабрика ``DeserializerFactory``, клиент работает только с ней.

    Общая часть вынесена сюда, в шаблонный метод ``deserialize``, чтобы не повторяться в каждой модели:

    - одна модель в JSON может встречаться много раз: полным словарём (единица измерения внутри каждой
      номенклатуры) или ссылкой ``{"id": ...}`` (базовая единица сама на себя). Собранные модели лежат
      в кэше по идентификатору, повторная встреча возвращает тот же объект, а не его копию;
    - конструкторы моделей не принимают идентификатор, поэтому он выставляется после создания;
    - у части данных идентификатора нет (ингредиент рецепта), такие данные в кэш не попадают.

    Наследник реализует только ``_build``: достаёт поля и вызывает конструктор. Вложенные модели он получает
    через функцию ``resolve``, это и есть рекурсия. Типы простых значений (строка, число) наследник не проверяет:
    это делает конструктор модели, поэтому правила модели не дублируются в десериализаторе.
    """

    # Функция фабрики: целевой тип и данные -> модель. Рекурсия идёт через неё
    _resolve: Callable[[type, object], object]
    # Собранные модели по идентификатору, общий для всех десериализаторов одной загрузки
    _cache: dict[uuid.UUID, BaseEntity]

    def __init__(self, resolve: Callable[[type, object], object], cache: dict[uuid.UUID, BaseEntity]) -> None:
        """Инициализирует десериализатор.

        :param resolve: Функция, превращающая данные вложенной модели в модель заданного типа.
        :param cache: Кэш собранных моделей по идентификатору, общий для всех десериализаторов.
        :raises ArgumentsException: Если ``resolve`` нельзя вызвать или ``cache`` не словарь.
        """
        self._resolve = CommonValidator.validate_callable(resolve, "resolve", "Ожидается функция десериализации")
        self._cache = cast(dict[uuid.UUID, BaseEntity], CommonValidator.validate_instance(
            cache, dict, "cache", "Ожидается словарь"
        ))

    def deserialize(self, data: object) -> object:
        """Превращает данные в модель, повторную встречу той же модели возвращает из кэша.

        Наследники метод не переопределяют, они реализуют ``_build``.

        :param data: Словарь полей модели или ссылка ``{"id": ...}`` на уже собранную модель.
        :return: Модель. Одному идентификатору всегда соответствует один и тот же объект.
        :raises ArgumentsException: Если данные не словарь со строковыми ключами, идентификатор некорректен или модель не собралась.
        :raises OperationException: Если ссылка указывает на модель, которой ещё нет в кэше.
        """
        fields = CommonValidator.validate_dict(data, "data")
        entity_id = self._read_id(fields)

        if entity_id is not None and entity_id in self._cache:
            return self._cache[entity_id]

        # В данных только идентификатор, а такой модели ещё нет: собрать её не из чего
        if entity_id is not None and len(fields) == 1:
            raise OperationException(f"Ссылка на неизвестный объект: {entity_id}")

        model = self._build(fields)
        if entity_id is not None:
            entity = CommonValidator.validate_instance(model, BaseEntity, "model", "Ожидается сущность с идентификатором")
            entity.id = entity_id
            self._cache[entity_id] = entity
        return model

    @abstractmethod
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт модель из полей данных через её конструктор.

        Вложенные модели берутся через ``self._resolve(ЦелевойТип, data["поле"])``. Вычисляемые поля,
        которые сериализатор тоже записал (``is_base``, ``gross_weight``), игнорируются: конструктор их не принимает.

        :param data: Словарь полей модели.
        :return: Новая модель. Идентификатор выставит ``deserialize``.
        :raises ArgumentsException: Если поля отсутствуют или некорректны.
        """

    def _nested[T](self, target_type: type[T], data: object) -> T:
        """Собирает вложенную модель заданного типа через функцию рекурсии.

        :param target_type: Тип вложенной модели.
        :param data: Словарь полей вложенной модели или ссылка ``{"id": ...}``.
        :return: Вложенная модель.
        :raises ArgumentsException: Если данные некорректны или десериализатор вернул модель другого типа.
        :raises OperationException: Если ссылка указывает на модель, которой ещё нет в кэше.
        """
        model = self._resolve(target_type, data)
        return CommonValidator.validate_instance(
            model, target_type, "data", f"Десериализатор вернул не {target_type.__name__}"
        )

    def _nested_list[T](self, target_type: type[T], data: object, field: str) -> list[T]:
        """Собирает список вложенных моделей заданного типа, каждый элемент — через функцию рекурсии.

        :param target_type: Тип элементов списка.
        :param data: Список словарей полей или ссылок.
        :param field: Имя поля для текста ошибки.
        :return: Список моделей в исходном порядке.
        :raises ArgumentsException: Если данные не список или элемент некорректен.
        :raises OperationException: Если элемент ссылается на модель, которой ещё нет в кэше.
        """
        items = cast(list[object], CommonValidator.validate_instance(data, list, field, "Ожидается список"))
        return [self._nested(target_type, item) for item in items]

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
