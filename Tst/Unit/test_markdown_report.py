from Src.Dtos.markdown_report_result import MarkdownReportResult
from Src.Logics.markdown_report import MarkdownReport
from Src.Logics.storage_manager import StorageManager
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def test_build_derived_range_returns_heading_and_field_list(first_start_storage: StorageManager):
    """Отчёт по единице — заголовок с наименованием и маркированный список всех полей, ссылка с кодом."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    result = MarkdownReport().build(kilogram)

    # Проверка
    assert isinstance(result, MarkdownReportResult)
    assert result.text == "\n".join(
        [
            "# килограмм",
            "",
            f"- **id**: {kilogram.id}",
            "- **name**: килограмм",
            f"- **base**: грамм (`{kilogram.base.id}`)",
            "- **factor**: 1000",
            "- **is_base**: False",
            "",
        ]
    )


def test_build_recipe_numbers_steps_and_items_in_order(first_start_storage: StorageManager):
    """Шаги и ингредиенты карты нумеруются в порядке состава, первое поле ингредиента стоит на строке номера."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    lines = MarkdownReport().build(recipe).text.split("\n")

    # Проверка
    for number, step in enumerate(recipe.steps, start=1):
        assert f"  {number}. {step}" in lines
    item_lines = [line for line in lines if " - **nomenclature**: " in line]
    assert item_lines == [
        f"  {number}. - **nomenclature**: {item.nomenclature.name} (`{item.nomenclature.id}`)"
        for number, item in enumerate(recipe.items, start=1)
    ]


def test_build_recipe_item_fields_are_aligned_inside_list_item(first_start_storage: StorageManager):
    """Остальные поля ингредиента выровнены по тексту после номера: так они остаются внутри пункта."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")
    beet = recipe.items[0]

    # Действие
    lines = MarkdownReport().build(recipe).text.split("\n")

    # Проверка
    start = lines.index(f"  1. - **nomenclature**: Свёкла (`{beet.nomenclature.id}`)")
    assert lines[start + 1 : start + 6] == [
        "     - **quantity**: 400",
        "     - **loss_ratio**: 0.05",
        "     - **base**:",
        "     - **gross_weight**: 400",
        "     - **net_weight**: 380",
    ]


def test_build_recipe_with_semi_finished_nests_base_items(first_start_storage: StorageManager):
    """Основание полуфабриката в борще выводится вложенным нумерованным списком под полем base."""
    # Подготовка
    borscht = find_recipe(first_start_storage, "Борщ с говядиной")
    bouillon = next(item for item in borscht.items if item.base)

    # Действие
    lines = MarkdownReport().build(borscht).text.split("\n")

    # Проверка
    start = lines.index(next(line for line in lines if f"(`{bouillon.nomenclature.id}`)" in line))
    nested = [line for line in lines[start + 1 :] if line.startswith("       ") and "**nomenclature**" in line]
    expected = [
        f"       {number}. - **nomenclature**: {item.nomenclature.name} (`{item.nomenclature.id}`)"
        for number, item in enumerate(bouillon.base, start=1)
    ]
    assert nested[: len(expected)] == expected


def test_build_name_with_markup_chars_escapes_them():
    """Служебные символы Markdown в значениях экранируются и в заголовке, и в списке полей."""
    # Подготовка
    unit = RangeModel("*кг_[x]#", 1)

    # Действие
    lines = MarkdownReport().build(unit).text.split("\n")

    # Проверка
    assert lines[0] == "# \\*кг\\_\\[x\\]\\#"
    assert "- **name**: \\*кг\\_\\[x\\]\\#" in lines
