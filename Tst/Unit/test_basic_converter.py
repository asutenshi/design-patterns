import uuid

import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.basic_converter import BasicConverter
from Src.Models.nomenclature_group_model import NomenclatureGroupModel

_CODE = uuid.UUID("12345678-1234-5678-1234-567812345678")


# Подготовка
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (42, 42),
        (-1.5, -1.5),
        (True, True),
        ("Мука", "Мука"),
        ("", ""),
        (None, None),
        (NomenclatureType.DISH, "блюдо"),
        (_CODE, "12345678-1234-5678-1234-567812345678"),
    ],
    ids=["int", "float", "bool", "str", "empty_str", "none", "enum", "uuid"],
)
def test_convert_simple_value_returns_field_with_value(value: object, expected: object):
    """Простое значение записывается под наименованием поля: числа, строки, bool и None как есть,
    перечисление — своим значением, UUID — строкой."""
    # Подготовка
    converter = BasicConverter()

    # Действие
    result = converter.convert("field", value)

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"field": expected}
    assert type(result["field"]) is type(expected)


def test_convert_field_with_spaces_returns_stripped_key():
    """Наименование поля очищается от пробелов по краям, как наименования сущностей."""
    # Действие
    result = BasicConverter().convert("  name  ", "Мука")

    # Проверка
    assert result == {"name": "Мука"}


# Подготовка
@pytest.mark.parametrize("field", ["", "   ", 1, None], ids=["empty", "spaces", "int", "none"])
def test_convert_invalid_field_raises(field: object):
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = BasicConverter().convert(field, "Мука")  # pyright: ignore[reportArgumentType]


# Подготовка
@pytest.mark.parametrize(
    "value",
    [NomenclatureGroupModel("Мясо"), ["Мука"], {"name": "Мука"}],
    ids=["model", "list", "dict"],
)
def test_convert_not_simple_value_raises(value: object):
    """Составное значение не простое: его обрабатывают конвертеры ссылок и списков."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = BasicConverter().convert("field", value)
