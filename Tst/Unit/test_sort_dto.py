import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.sort_order import SortOrder
from Src.Dtos.sort_dto import SortDto


def test_init_defaults_direction_to_asc():
    """Без явного направления сортировка по умолчанию выполняется по возрастанию."""
    # Действие
    dto = SortDto("  period  ")

    # Проверка
    assert dto.field_name == "period"
    assert dto.direction is SortOrder.ASC


def test_from_dict_valid_values_creates_sort_dto():
    """Фабричный метод собирает SortDto из словаря с явным направлением."""
    # Действие
    dto = SortDto.from_dict({"field_name": "level", "direction": "DESC"})

    # Проверка
    assert dto.field_name == "level"
    assert dto.direction is SortOrder.DESC


def test_from_dict_without_direction_defaults_to_asc():
    """Отсутствующее поле direction в словаре трактуется как ASC."""
    # Действие
    dto = SortDto.from_dict({"field_name": "period"})

    # Проверка
    assert dto.direction is SortOrder.ASC


# Подготовка
@pytest.mark.parametrize(
    "data",
    [
        {},
        {"field_name": "   "},
        {"field_name": "period", "direction": "UP"},
    ],
)
def test_from_dict_invalid_data_raises(data: dict[str, object]):
    """Пустое поле или неизвестное направление отклоняются исключением ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = SortDto.from_dict(data)
