import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.filter_type import FilterType
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.filter_item_dto import FilterItemDto


def test_from_dict_valid_data_builds_filter_items():
    """Тело запроса превращается в набор условий с типом сравнения из перечисления."""
    # Подготовка
    data: dict[str, object] = {
        "filters": [
            {"field_name": "range.base.name", "filter_type": "EQUALS", "value": "грамм"},
            {"field_name": "name", "filter_type": "LIKE", "value": "Говядина"},
        ]
    }

    # Действие
    result = FilterDto.from_dict(data).filters

    # Проверка
    assert [item.field_name for item in result] == ["range.base.name", "name"]
    assert [item.filter_type for item in result] == [FilterType.EQUALS, FilterType.LIKE]
    assert [item.value for item in result] == ["грамм", "Говядина"]


def test_from_dict_empty_filters_returns_empty_set():
    """Пустой список условий допустим: такой фильтр ничего не ограничивает."""
    # Подготовка
    data: dict[str, object] = {"filters": []}

    # Действие
    result = FilterDto.from_dict(data)

    # Проверка
    assert result.filters == []


# Подготовка
@pytest.mark.parametrize(
    "data",
    [
        {},
        {"filters": "name"},
        {"filters": ["name"]},
        {"filters": [{"filter_type": "LIKE", "value": "а"}]},
        {"filters": [{"field_name": "name", "value": "а"}]},
        {"filters": [{"field_name": "name", "filter_type": "LIKE"}]},
        {"filters": [{"field_name": "name", "filter_type": "CONTAINS", "value": "а"}]},
        {"filters": [{"field_name": " ", "filter_type": "LIKE", "value": "а"}]},
        {"filters": [{"field_name": "name", "filter_type": "LIKE", "value": ""}]},
    ],
)
def test_from_dict_invalid_data_raises(data: dict[str, object]):
    """Некорректное тело запроса отклоняется ошибкой аргумента."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = FilterDto.from_dict(data)


def test_filters_changing_returned_list_keeps_dto_unchanged():
    """Свойство отдаёт копию: изменение полученного списка не меняет набор условий."""
    # Подготовка
    item = FilterItemDto("name", FilterType.EQUALS, "Соль")
    dto = FilterDto([item])

    # Действие
    dto.filters.clear()

    # Проверка
    assert dto.filters == [item]
