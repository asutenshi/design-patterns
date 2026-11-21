from typing import Self, cast

from Src.Core.common_validator import CommonValidator
from Src.Core.filter_type import FilterType


class FilterItemDto:
    """Одно условие фильтрации: путь к полю модели, способ сравнения и искомое значение.

    Путь записывается через точку и может вести во вложенные модели, например ``range.base.name``.
    Существование поля здесь не проверяется: DTO не знает, к какой модели применится условие.
    """

    # Путь к полю модели
    _field_name: str
    # Способ сравнения
    _filter_type: FilterType
    # Искомое значение
    _value: str

    def __init__(self, field_name: str, filter_type: FilterType, value: str) -> None:
        """Инициализирует условие фильтрации.

        :param field_name: Путь к полю модели через точку.
        :param filter_type: Способ сравнения.
        :param value: Искомое значение.
        :raises ArgumentsException: Если путь или значение не непустая строка либо способ сравнения неверного типа.
        """
        self._field_name = CommonValidator.validate_string(field_name, "field_name")
        self._filter_type = CommonValidator.validate_instance(
            filter_type, FilterType, "filter_type", "Ожидается способ сравнения"
        )
        self._value = CommonValidator.validate_string(value, "value")

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт условие по полям ``field_name``, ``filter_type`` и ``value``.

        :param data: Поля условия из тела запроса.
        :return: Новое условие фильтрации.
        :raises ArgumentsException: Если данные не словарь, поля нет или значение некорректно.
        """
        fields = CommonValidator.validate_dict(data, "data")
        return cls(
            field_name=cast(str, CommonValidator.validate_field(fields, "field_name")),
            filter_type=CommonValidator.validate_enum(
                CommonValidator.validate_field(fields, "filter_type"), FilterType, "filter_type"
            ),
            value=cast(str, CommonValidator.validate_field(fields, "value")),
        )

    @property
    def field_name(self) -> str:
        """Возвращает путь к полю модели."""
        return self._field_name

    @property
    def filter_type(self) -> FilterType:
        """Возвращает способ сравнения."""
        return self._filter_type

    @property
    def value(self) -> str:
        """Возвращает искомое значение."""
        return self._value
