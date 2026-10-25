import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Logics.basic_converter import BasicConverter
from Src.Logics.collection_converter import CollectionConverter

# Здесь проверяется сам конвертер: функция конвертации элемента подменяется заглушкой.
# Списки настоящих моделей через фабрику проверяются в test_converter_factory.


def _same(item: object) -> object:
    """Заглушка конвертации: элемент возвращается как есть."""
    return item


# Подготовка
@pytest.mark.parametrize(
    "value",
    [["Нарезать", "Варить", "Подать"], ("Нарезать", "Варить", "Подать")],
    ids=["list", "tuple"],
)
def test_convert_collection_of_simple_values_returns_field_with_list(value: object):
    """Список и кортеж записываются списком данных элементов в исходном порядке."""
    # Подготовка
    converter = CollectionConverter(_same)

    # Действие
    result = converter.convert("steps", value)

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"steps": ["Нарезать", "Варить", "Подать"]}


def test_convert_empty_collection_returns_field_with_empty_list():
    """Пустой список записывается пустым списком."""
    # Действие
    result = CollectionConverter(_same).convert("items", [])

    # Проверка
    assert result == {"items": []}


def test_convert_collection_returns_converted_data_of_each_item():
    """Каждый элемент передаётся функции конвертации, в список попадает то, что она вернула."""
    # Подготовка
    converted: list[object] = []

    def convert_item(item: object) -> object:
        converted.append(item)
        return {"value": item}

    # Действие
    result = CollectionConverter(convert_item).convert("items", ["Мука", 1.5])

    # Проверка
    assert result == {"items": [{"value": "Мука"}, {"value": 1.5}]}
    assert converted == ["Мука", 1.5]


def test_convert_item_raises_propagates_error():
    """Ошибку конвертации элемента конвертер не скрывает."""

    # Подготовка
    def convert_item(_: object) -> object:
        raise ArgumentsException("source", "Ожидается объект с публичными свойствами")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(convert_item).convert("items", ["Мука"])


# Подготовка
@pytest.mark.parametrize("value", ["Мука", {"a": 1}, {1, 2}, None], ids=["str", "dict", "set", "none"])
def test_convert_not_list_or_tuple_raises(value: object):
    """Строка, словарь, множество и None не обрабатываются как список."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(_same).convert("items", value)


# Подготовка
@pytest.mark.parametrize("convert_item", [None, BasicConverter()], ids=["none", "converter_instead_of_function"])
def test_init_not_callable_convert_item_raises(convert_item: object):
    """Функцию конвертации элемента проверяет конструктор: сам конвертер вместо функции не подходит."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(convert_item)  # pyright: ignore[reportArgumentType]


def test_convert_invalid_field_raises():
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(_same).convert("", ["Мука"])
