import uuid
from typing import override
from abc import ABC

from Src.Core.exception import arguments_exception


class base_entity(ABC):
    """Абстрактный базовый класс для идентифицируемых сущностей."""

    # Уникальный идентификатор сущности
    _id: uuid.UUID
    # Наименование сущности
    _name: str

    def __init__(self, name: str) -> None:
        """Инициализирует базовый экземпляр сущности.

        :param name: Наименование сущности.
        :raises arguments_exception: Если наименование не строка, пустое или состоит из пробелов.
        """
        self._id = uuid.uuid4()
        self.name = name

    @property
    def id(self) -> uuid.UUID:
        """Возвращает уникальный идентификатор сущности."""
        return self._id

    @id.setter
    def id(self, value: uuid.UUID) -> None:
        """
        Устанавливает уникальный идентификатор сущности.

        :param value: Новый идентификатор сущности.
        :raises arguments_exception: Если значение не UUID.
        """
        if not isinstance(value, uuid.UUID):
            raise arguments_exception("value", "Некорректно передан параметр идентификатора")
            
        self._id = value
        
    @property
    def name(self) -> str:
        """Возвращает наименование сущности."""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """
        Устанавливает наименование сущности.

        :param value: Новое наименование сущности.
        :raises arguments_exception: Если значение не строка, пустое или состоит из пробелов.
        """
        if not isinstance(value, str):
            raise arguments_exception("value", "Некорректно передан параметр наименования")
        cleaned_value = value.strip()
        if not cleaned_value:
            raise arguments_exception("value", "Некорректно передан параметр наименования")

        self._name = cleaned_value

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