import xml.etree.ElementTree as ET

from Src.Dtos.report_result import ReportResult
from Src.Logics.storage_manager import StorageManager
from Src.Logics.xml_report import XmlReport
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def child(element: ET.Element, tag: str) -> ET.Element:
    """Возвращает дочерний элемент по имени, падает, если его нет."""
    found = element.find(tag)
    assert found is not None
    return found


def test_build_derived_range_returns_element_per_field(first_start_storage: StorageManager):
    """Корень назван по классу, поля — дочерние элементы по порядку, ссылка — наименование и атрибут id."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    result = XmlReport().build(kilogram)

    # Проверка
    assert isinstance(result, ReportResult)
    assert result.text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')
    root = ET.fromstring(result.binary)
    assert root.tag == "RangeModel"
    assert [(element.tag, element.text, element.attrib) for element in root] == [
        ("id", str(kilogram.id), {}),
        ("name", "килограмм", {}),
        ("base", "грамм", {"id": str(kilogram.base.id)}),
        ("factor", "1000", {}),
        ("is_base", "False", {}),
    ]


def test_build_recipe_lists_steps_and_items_as_item_elements(first_start_storage: StorageManager):
    """Шаги и ингредиенты карты — элементы item в порядке состава, номенклатура ингредиента — ссылка с id."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    root = ET.fromstring(XmlReport().build(recipe).binary)

    # Проверка
    assert [item.text for item in child(root, "steps")] == recipe.steps
    items = list(child(root, "items"))
    assert [(child(item, "nomenclature").text, child(item, "nomenclature").get("id")) for item in items] == [
        (item.nomenclature.name, str(item.nomenclature.id)) for item in recipe.items
    ]
    assert child(items[0], "quantity").text == "400"
    assert len(child(items[0], "base")) == 0


def test_build_recipe_with_semi_finished_nests_base_items(first_start_storage: StorageManager):
    """Основание полуфабриката в борще — вложенные элементы item внутри base."""
    # Подготовка
    borscht = find_recipe(first_start_storage, "Борщ с говядиной")
    index, bouillon = next((index, item) for index, item in enumerate(borscht.items) if item.base)

    # Действие
    root = ET.fromstring(XmlReport().build(borscht).binary)

    # Проверка
    base = child(list(child(root, "items"))[index], "base")
    assert [child(part, "nomenclature").get("id") for part in base] == [
        str(part.nomenclature.id) for part in bouillon.base
    ]


def test_build_name_with_markup_chars_is_escaped():
    """Символы разметки XML в значении экранируются: документ разбирается, значение не искажается."""
    # Подготовка
    unit = RangeModel("<кг> & \"г\"", 1)

    # Действие
    result = XmlReport().build(unit)

    # Проверка
    assert "<кг>" not in result.text
    assert child(ET.fromstring(result.binary), "name").text == "<кг> & \"г\""
