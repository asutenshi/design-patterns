from Src.Core.base_entity import BaseEntity
from Src.Core.validator import Validator


class NamedEntity(BaseEntity):
    """Абстрактный базовый класс для сущностей с обязательным наименованием."""

    # Наименование сущности
    _name: str

    def __init__(self, name: str) -> None:
        """Инициализирует сущность с наименованием.

        :param name: Наименование сущности.
        :raises ArgumentsException: Если наименование не строка, пустое или состоит из пробелов.
        """
        super().__init__()
        self.name = name

    @property
    def name(self) -> str:
        """Возвращает наименование сущности."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """
        Устанавливает наименование сущности.

        :param value: Новое наименование сущности.
        :raises ArgumentsException: Если значение не строка, пустое или состоит из пробелов.
        """
        self._name = Validator.validate_string(value, "name")
