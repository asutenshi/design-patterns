from typing import Self

from Src.Core.common_validator import CommonValidator
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.sort_dto import SortDto
from Src.Logics.deserializer_factory import DeserializerFactory


class LogQueryDto:
    """Параметры запроса журнала логов: условия фильтрации и необязательная сортировка."""

    # Условия отбора записей лога
    _filter: FilterDto
    # Параметры сортировки результата или None
    _sort: SortDto | None

    def __init__(self, filter_dto: FilterDto | None = None, sort_dto: SortDto | None = None) -> None:
        """Инициализирует параметры запроса логов.

        :param filter_dto: Условия отбора записей; ``None`` — пустой фильтр без ограничений.
        :param sort_dto: Параметры сортировки; ``None`` — исходный порядок поступления.
        :raises ArgumentsException: Если фильтр или сортировка неверного типа.
        """
        self._filter = (
            FilterDto([])
            if filter_dto is None
            else CommonValidator.validate_instance(filter_dto, FilterDto, "filter_dto", "Ожидаются условия фильтра")
        )
        self._sort = (
            None
            if sort_dto is None
            else CommonValidator.validate_instance(sort_dto, SortDto, "sort_dto", "Ожидаются параметры сортировки")
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт запрос по необязательным полям ``filters`` и ``sort``.

        :param data: Тело запроса из API.
        :return: Новый объект ``LogQueryDto``.
        :raises ArgumentsException: Если данные не словарь либо фильтр или сортировка некорректны.
        """
        fields = CommonValidator.validate_dict(data, "data")
        filter_dto = DeserializerFactory().deserialize_as(FilterDto, fields)
        raw_sort = fields.get("sort")
        sort_dto = None if raw_sort is None else DeserializerFactory().deserialize_as(SortDto, raw_sort)
        return cls(filter_dto=filter_dto, sort_dto=sort_dto)

    @property
    def filter(self) -> FilterDto:
        """Возвращает условия фильтрации записей лога."""
        return self._filter

    @property
    def sort(self) -> SortDto | None:
        """Возвращает параметры сортировки или None."""
        return self._sort
