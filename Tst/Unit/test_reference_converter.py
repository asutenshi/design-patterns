import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Logics.reference_converter import ReferenceConverter
from Src.Models.nomenclature_group_model import NomenclatureGroupModel

# Здесь проверяется сам конвертер: функция раскрытия подменяется заглушкой.
# Раскрытие настоящих моделей через фабрику проверяется в test_converter_factory.


def test_convert_model_returns_field_with_expanded_dict():
    """Вложенный объект передаётся функции раскрытия, её словарь записывается под наименованием поля."""
    # Подготовка
    group = NomenclatureGroupModel("Мясо")
    expanded: list[object] = []

    def expand(source: object) -> dict[str, object]:
        expanded.append(source)
        return {"name": "Мясо"}

    converter = ReferenceConverter(expand)

    # Действие
    result = converter.convert("group", group)

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"group": {"name": "Мясо"}}
    assert expanded == [group]
    assert expanded[0] is group


def test_convert_expand_raises_propagates_error():
    """Ошибку функции раскрытия конвертер не скрывает."""

    # Подготовка
    def expand(_: object) -> dict[str, object]:
        raise ArgumentsException("source", "Ожидается объект с полями")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReferenceConverter(expand).convert("group", 1)


# Подготовка
@pytest.mark.parametrize("expand", [None, {"name": "Мясо"}], ids=["none", "dict"])
def test_init_not_callable_expand_raises(expand: object):
    """Функцию раскрытия проверяет конструктор: ошибка видна сразу, а не при первой конвертации."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReferenceConverter(expand)  # pyright: ignore[reportArgumentType]


def test_convert_invalid_field_raises():
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReferenceConverter(lambda _: {}).convert("", NomenclatureGroupModel("Мясо"))
