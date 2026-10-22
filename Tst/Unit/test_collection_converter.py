import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Logics.basic_converter import BasicConverter
from Src.Logics.collection_converter import CollectionConverter
from Src.Logics.reference_converter import ReferenceConverter

# Здесь проверяется сам конвертер: функция выбора конвертера подменяется заглушкой.
# Списки настоящих моделей через фабрику проверяются в test_converter_factory.


def _basic(_: object) -> AbstractConverter:
    """Заглушка выбора конвертера: любой элемент — простое значение."""
    return BasicConverter()


# Подготовка
@pytest.mark.parametrize(
    "value",
    [["Нарезать", "Варить", "Подать"], ("Нарезать", "Варить", "Подать")],
    ids=["list", "tuple"],
)
def test_convert_collection_of_simple_values_returns_field_with_list(value: object):
    """Список и кортеж записываются списком значений элементов в исходном порядке."""
    # Подготовка
    converter = CollectionConverter(_basic)

    # Действие
    result = converter.convert("steps", value)

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"steps": ["Нарезать", "Варить", "Подать"]}


def test_convert_empty_collection_returns_field_with_empty_list():
    """Пустой список записывается пустым списком."""
    # Действие
    result = CollectionConverter(_basic).convert("items", [])

    # Проверка
    assert result == {"items": []}


def test_convert_collection_of_objects_returns_list_of_element_data():
    """Элемент списка обрабатывается выбранным для него конвертером, в список попадают только его данные."""
    # Подготовка
    reference = ReferenceConverter(lambda source: {"value": source})

    def create(item: object) -> AbstractConverter:
        return BasicConverter() if isinstance(item, str) else reference

    # Действие
    result = CollectionConverter(create).convert("items", ["Мука", 1.5])

    # Проверка
    assert result == {"items": ["Мука", {"value": 1.5}]}


def test_convert_nested_collection_returns_nested_list():
    """Список списков записывается вложенными списками: конвертер списков выбирается и для элемента."""
    # Подготовка
    converters: list[CollectionConverter] = []

    def create(item: object) -> AbstractConverter:
        return converters[0] if isinstance(item, list) else BasicConverter()

    converters.append(CollectionConverter(create))

    # Действие
    result = converters[0].convert("matrix", [[1, 2], [3]])

    # Проверка
    assert result == {"matrix": [[1, 2], [3]]}


# Подготовка
@pytest.mark.parametrize("value", ["Мука", {"a": 1}, {1, 2}, None], ids=["str", "dict", "set", "none"])
def test_convert_not_list_or_tuple_raises(value: object):
    """Строка, словарь, множество и None не обрабатываются как список."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(_basic).convert("items", value)


# Подготовка
@pytest.mark.parametrize("create", [None, BasicConverter()], ids=["none", "converter_instead_of_function"])
def test_init_not_callable_create_raises(create: object):
    """Функцию выбора конвертера проверяет конструктор: сам конвертер вместо функции не подходит."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(create)  # pyright: ignore[reportArgumentType]


def test_convert_invalid_field_raises():
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = CollectionConverter(_basic).convert("", ["Мука"])
