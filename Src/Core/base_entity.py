import uuid
from abc import ABC
from typing import override

from Src.Core.exception import ArgumentsException


class BaseEntity(ABC):
    """Абстрактный базовый класс для идентифицируемых сущностей.

    Хранит только идентификатор и определяет равенство и хэш по нему.
    Сущности без наименования (остатки, записи журнала, документы) наследуются отсюда,
    сущности с наименованием — от NamedEntity.
    """

    # Уникальный идентификатор сущности
    _id: uuid.UUID

    def __init__(self) -> None:
        """Инициализирует базовый экземпляр сущности с новым идентификатором."""
        self._id = uuid.uuid4()

    @property
    def id(self) -> uuid.UUID:
        """Возвращает уникальный идентификатор сущности."""
        return self._id

    @id.setter
    def id(self, value: uuid.UUID) -> None:
        """
        Устанавливает уникальный идентификатор сущности.

        :param value: Новый идентификатор сущности.
        :raises ArgumentsException: Если значение не UUID.
        """
        if not isinstance(value, uuid.UUID):
            raise ArgumentsException("value", "Некорректно передан параметр идентификатора")

        self._id = value

    @override
    def __eq__(self, value: object, /) -> bool:
        """Сравнивает сущности по типу и идентификатору."""
        if type(value) is not type(self):
            return NotImplemented
        return self._id == value._id

    @override
    def __hash__(self) -> int:
        """Возвращает хэш сущности на основе её идентификатора."""
        return hash(self._id)

# В будущем я бы добавл repr для удобной отладки
# Также стоило бы реализовать восстановление сущности по ее известному id, но это уже когда появится БД
# Сейчас ABC не делает клсс абстрактным тк abstractmethod нигде не применен
