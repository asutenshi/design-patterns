import uuid
from abc import ABC


class base_entity(ABC):
    """Абстрактный базовый класс для идентифицируемых сущностей."""

    # Уникальный идентификатор сущности
    _id: uuid.UUID
    # Наименование сущности
    _name: str

    def __init__(self, name: str) -> None:
        """Инициализирует базовый экземпляр сущности.

        :param name: Наименование сущности.
        :raises TypeError: Если наименование не строка.
        :raises ValueError: Если наименование пустое.
        """
        self._id = uuid.uuid4()
        self.name = name

    @property
    def id(self) -> uuid.UUID:
        """Возвращает уникальный идентификатор сущности."""
        return self._id

    @property
    def name(self) -> str:
        """Возвращает наименование сущности."""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """
        Устанавливает наименование сущности.

        :param value: Новое наименование сущности.
        :raises TypeError: Если значение не строка.
        :raises ValueError: Если значение пустое или состоит из пробелов.
        """
        if not isinstance(value, str):
            raise TypeError("Наименование должно быть строкой")
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Наименование не может быть пустым")

        self._name = cleaned_value

# В будущем я бы добавл repr для удобной отладки, eq и hash для реализации идентичности класса
# Также стоило бы реализовать восстановление сущности по ее известному id, но это уже когда появится БД
# Сейчас ABC не делает клсс абстрактным тк abstractmethod нигде не применен