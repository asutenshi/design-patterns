from typing import Self, cast

from Src.Core.common_validator import CommonValidator
from Src.Core.sort_order import SortOrder


class SortDto:
    """Параметры сортировки коллекции моделей: путь к полю и направление."""

    # Путь к полю модели через точку
    _field_name: str
    # Направление сортировки
    _direction: SortOrder

    def __init__(self, field_name: str, direction: SortOrder = SortOrder.ASC) -> None:
        """Инициализирует параметры сортировки.

        :param field_name: Путь к публичному полю модели через точку.
        :param direction: Направление сортировки, по умолчанию по возрастанию.
        :raises ArgumentsException: Если имя поля пусто или направление не является ``SortOrder``.
        """
        self._field_name = CommonValidator.validate_string(field_name, "field_name")
        self._direction = CommonValidator.validate_instance(
            direction, SortOrder, "direction", "Ожидается направление сортировки"
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт параметры сортировки по полям ``field_name`` и ``direction``.

        Поле ``direction`` необязательно: по умолчанию используется ``ASC``.

        :param data: Словарь параметров сортировки из тела запроса.
        :return: Новый объект ``SortDto``.
        :raises ArgumentsException: Если данные не словарь, нет ``field_name`` или направление неизвестно.
        """
        fields = CommonValidator.validate_dict(data, "data")
        field_name = cast(str, CommonValidator.validate_field(fields, "field_name"))
        direction = CommonValidator.validate_enum(fields.get("direction", SortOrder.ASC), SortOrder, "direction")
        return cls(field_name=field_name, direction=direction)

    @property
    def field_name(self) -> str:
        """Возвращает путь к полю сортировки."""
        return self._field_name

    @property
    def direction(self) -> SortOrder:
        """Возвращает направление сортировки."""
        return self._direction
