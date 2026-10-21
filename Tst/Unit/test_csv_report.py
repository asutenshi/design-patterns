import csv
import io

from Src.Dtos.report_result import ReportResult
from Src.Logics.csv_report import CsvReport
from Src.Logics.storage_manager import StorageManager
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def parse(text: str) -> list[list[str]]:
    """Разбирает текст CSV с разделителем «;» в список строк таблицы."""
    return list(csv.reader(io.StringIO(text), delimiter=";"))


def test_build_derived_range_returns_header_and_row_per_field(first_start_storage: StorageManager):
    """Отчёт по единице — заголовок и по строке «поле;значение» на каждое поле, ссылка с кодом."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    result = CsvReport().build(kilogram)

    # Проверка
    assert isinstance(result, ReportResult)
    assert parse(result.text) == [
        ["field", "value"],
        ["id", str(kilogram.id)],
        ["name", "килограмм"],
        ["base", f"грамм [{kilogram.base.id}]"],
        ["factor", "1000"],
        ["is_base", "False"],
    ]


def test_build_recipe_rows_have_numbered_paths_for_steps_and_items(first_start_storage: StorageManager):
    """Шаги и ингредиенты получают пути с номером элемента с единицы, в порядке состава."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    rows = dict(map(tuple, parse(CsvReport().build(recipe).text)))

    # Проверка
    for number, step in enumerate(recipe.steps, start=1):
        assert rows[f"steps[{number}]"] == step
    for number, item in enumerate(recipe.items, start=1):
        assert rows[f"items[{number}].nomenclature"] == f"{item.nomenclature.name} [{item.nomenclature.id}]"
    assert rows["items[1].quantity"] == "400"
    assert rows["items[1].net_weight"] == "380"


def test_build_raw_material_item_keeps_empty_base_row(first_start_storage: StorageManager):
    """Пустое основание сырья не пропадает из таблицы: для него строка с пустым значением."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    rows = parse(CsvReport().build(recipe).text)

    # Проверка
    assert ["items[1].base", ""] in rows


def test_build_recipe_with_semi_finished_expands_base_paths(first_start_storage: StorageManager):
    """Основание полуфабриката в борще разворачивается в пути вида items[i].base[j]."""
    # Подготовка
    borscht = find_recipe(first_start_storage, "Борщ с говядиной")
    number, bouillon = next((number, item) for number, item in enumerate(borscht.items, start=1) if item.base)

    # Действие
    rows = dict(map(tuple, parse(CsvReport().build(borscht).text)))

    # Проверка
    for index, part in enumerate(bouillon.base, start=1):
        assert rows[f"items[{number}].base[{index}].nomenclature"] == f"{part.nomenclature.name} [{part.nomenclature.id}]"


def test_build_name_with_delimiter_and_quotes_is_quoted():
    """Значение с разделителем и кавычками экранируется и читается обратно без искажений."""
    # Подготовка
    unit = RangeModel('кг; "особый"', 1)

    # Действие
    rows = parse(CsvReport().build(unit).text)

    # Проверка
    assert ["name", 'кг; "особый"'] in rows
