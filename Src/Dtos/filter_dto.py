from typing import Self, cast

from Src.Core.common_validator import CommonValidator
from Src.Dtos.filter_item_dto import FilterItemDto


class FilterDto:
    """Набор условий фильтрации доменных моделей.

    Модель проходит фильтр, если выполнены все условия. Пустой набор допустим: такой фильтр пропускает всё.
    """

    # Условия фильтрации
    _filters: tuple[FilterItemDto, ...]

    def __init__(self, filters: list[FilterItemDto]) -> None:
        """Инициализирует набор условий.

        :param filters: Условия фильтрации, список может быть пустым.
        :raises ArgumentsException: Если передан не список или его элемент не является условием.
        """
        items = cast(list[object], CommonValidator.validate_instance(filters, list, "filters", "Ожидается список условий"))
        self._filters = tuple(
            CommonValidator.validate_instance(item, FilterItemDto, "filters", "Ожидается условие фильтрации")
            for item in items
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт набор условий по полю ``filters``.

        :param data: Тело запроса с условиями фильтрации.
        :return: Новый набор условий.
        :raises ArgumentsException: Если данные не словарь, поля нет, оно не список или условие некорректно.
        """
        fields = CommonValidator.validate_dict(data, "data")
        items = cast(
            list[object],
            CommonValidator.validate_instance(
                CommonValidator.validate_field(fields, "filters"), list, "filters", "Ожидается список условий"
            ),
        )
        return cls([FilterItemDto.from_dict(CommonValidator.validate_dict(item, "filters")) for item in items])

    @property
    def filters(self) -> list[FilterItemDto]:
        """Возвращает копию списка условий фильтрации."""
        return list(self._filters)
