import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Logics.dict_converter import DictConverter

# Здесь проверяется сам конвертер: функция конвертации значения подменяется заглушкой.
# Словари с настоящими моделями через фабрику проверяются в test_converter_factory.


def _same(item: object) -> object:
    """Заглушка конвертации: значение возвращается как есть."""
    return item


def test_convert_dict_returns_field_with_same_keys_in_order():
    """Словарь записывается словарём с теми же ключами в том же порядке."""
    # Подготовка
    converter = DictConverter(_same)

    # Действие
    result = converter.convert("totals", {"Мука": 400, "Соль": 5})

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"totals": {"Мука": 400, "Соль": 5}}
    assert list(result["totals"]) == ["Мука", "Соль"]  # pyright: ignore[reportArgumentType]


def test_convert_empty_dict_returns_field_with_empty_dict():
    """Пустой словарь записывается пустым словарём."""
    # Действие
    result = DictConverter(_same).convert("totals", {})

    # Проверка
    assert result == {"totals": {}}


def test_convert_dict_returns_converted_data_of_each_value():
    """Каждое значение передаётся функции конвертации, под своим ключом лежит то, что она вернула."""
    # Подготовка
    converted: list[object] = []

    def convert_value(item: object) -> object:
        converted.append(item)
        return [item]

    # Действие
    result = DictConverter(convert_value).convert("totals", {"Мука": 400, "Соль": 5})

    # Проверка
    assert result == {"totals": {"Мука": [400], "Соль": [5]}}
    assert converted == [400, 5]


def test_convert_value_raises_propagates_error():
    """Ошибку конвертации значения конвертер не скрывает."""

    # Подготовка
    def convert_value(_: object) -> object:
        raise ArgumentsException("source", "Ожидается объект с публичными свойствами")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DictConverter(convert_value).convert("totals", {"Мука": 400})


# Подготовка
@pytest.mark.parametrize("key", [1, None, ("Мука", "Соль")], ids=["int", "none", "tuple"])
def test_convert_not_string_key_raises(key: object):
    """Ключи JSON — строки, поэтому словарь с ключом другого типа не записывается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DictConverter(_same).convert("totals", {key: 400})


# Подготовка
@pytest.mark.parametrize("value", ["Мука", ["Мука"], {1, 2}, None], ids=["str", "list", "set", "none"])
def test_convert_not_dict_raises(value: object):
    """Строка, список, множество и None не обрабатываются как словарь."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DictConverter(_same).convert("totals", value)


# Подготовка
@pytest.mark.parametrize("convert_value", [None, {"Мука": 400}], ids=["none", "dict"])
def test_init_not_callable_convert_value_raises(convert_value: object):
    """Функцию конвертации значения проверяет конструктор: ошибка видна сразу, а не при первой конвертации."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DictConverter(convert_value)  # pyright: ignore[reportArgumentType]


def test_convert_invalid_field_raises():
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DictConverter(_same).convert("", {"Мука": 400})
