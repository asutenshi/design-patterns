import pytest
from Src.Core.exception import ArgumentsException
from Src.Dtos.txt_report_result import TxtReportResult
from Src.Logics.storage_manager import StorageManager
from Src.Logics.txt_report import TxtReport
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def test_build_base_range_returns_all_fields_and_self_reference(first_start_storage: StorageManager):
    """Отчёт по базовой единице содержит все её поля, а ссылка base на саму себя выводится ссылкой без зацикливания."""
    # Подготовка
    gram = next(item for item in first_start_storage.ranges if item.name == "грамм")

    # Действие
    result = TxtReport().build(gram)

    # Проверка
    assert result.text == "\n".join(
        [
            f"id: {gram.id}",
            "name: грамм",
            f"base: грамм [{gram.id}]",
            "factor: 1",
            "is_base: True",
        ]
    )


def test_build_derived_range_references_base_range(first_start_storage: StorageManager):
    """Производная единица ссылается на базовую её наименованием и кодом."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    lines = TxtReport().build(kilogram).text.split("\n")

    # Проверка
    assert f"base: грамм [{kilogram.base.id}]" in lines
    assert "factor: 1000" in lines
    assert "is_base: False" in lines


def test_build_nomenclature_references_group_and_range_and_shows_type_value(first_start_storage: StorageManager):
    """Группа и единица номенклатуры выводятся ссылками, тип — значением перечисления."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")

    # Действие
    lines = TxtReport().build(beet).text.split("\n")

    # Проверка
    assert lines == [
        f"id: {beet.id}",
        "name: Свёкла",
        "full_name: Свёкла столовая свежая",
        f"group: Овощи [{beet.group.id}]",
        f"range: килограмм [{beet.range.id}]",
        "type: сырьё",
        "grams_per_base_unit: 1",
    ]


def test_build_recipe_lists_steps_and_every_item_in_order(first_start_storage: StorageManager):
    """Отчёт по карте содержит все шаги и по элементу списка на каждый ингредиент, в порядке состава."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    lines = TxtReport().build(recipe).text.split("\n")

    # Проверка
    assert f"result: Зажарка свекольная [{recipe.result.id}]" in lines
    for step in recipe.steps:
        assert f"  - {step}" in lines
    item_lines = [line for line in lines if line.startswith("  - nomenclature: ")]
    assert item_lines == [
        f"  - nomenclature: {item.nomenclature.name} [{item.nomenclature.id}]" for item in recipe.items
    ]


def test_build_recipe_item_fields_are_aligned_under_bullet(first_start_storage: StorageManager):
    """Поля ингредиента идут под маркером с выравниванием по его тексту, веса округлены."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")
    beet = recipe.items[0]

    # Действие
    lines = TxtReport().build(recipe).text.split("\n")

    # Проверка
    start = lines.index(f"  - nomenclature: Свёкла [{beet.nomenclature.id}]")
    assert lines[start + 1 : start + 6] == [
        "    quantity: 400",
        "    loss_ratio: 0.05",
        "    base:",
        "    gross_weight: 400",
        "    net_weight: 380",
    ]


def test_build_recipe_with_semi_finished_expands_base_recursively(first_start_storage: StorageManager):
    """Полуфабрикат в составе борща раскрывается по основанию: его ингредиенты идут уровнем глубже."""
    # Подготовка
    borscht = find_recipe(first_start_storage, "Борщ с говядиной")
    bouillon = next(item for item in borscht.items if item.nomenclature.name == "Бульон костный говяжий")

    # Действие
    lines = TxtReport().build(borscht).text.split("\n")

    # Проверка
    start = lines.index(f"  - nomenclature: Бульон костный говяжий [{bouillon.nomenclature.id}]")
    nested = [line for line in lines[start:] if line.startswith("      - nomenclature: ")]
    expected = [f"      - nomenclature: {item.nomenclature.name} [{item.nomenclature.id}]" for item in bouillon.base]
    assert nested[: len(expected)] == expected


def test_build_recipe_weights_match_model(first_start_storage: StorageManager):
    """Итоговые веса карты в отчёте совпадают с вычисленными моделью."""
    # Подготовка
    report = TxtReport()
    borscht = find_recipe(first_start_storage, "Борщ с говядиной")

    # Действие
    lines = report.build(borscht).text.split("\n")

    # Проверка
    assert f"gross_weight: {report._format_scalar(borscht.gross_weight)}" in lines  # pyright: ignore[reportPrivateUsage]
    assert f"net_weight: {report._format_scalar(borscht.net_weight)}" in lines  # pyright: ignore[reportPrivateUsage]


def test_build_same_source_twice_returns_equal_results(first_start_storage: StorageManager):
    """Два отчёта по одной сущности равны: результат сравнивается по содержимому."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Борщ с говядиной")

    # Действие
    first = TxtReport().build(recipe)
    second = TxtReport().build(recipe)

    # Проверка
    assert isinstance(first, TxtReportResult)
    assert first == second
    assert first is not second


# Подготовка
@pytest.mark.parametrize("source", [None, "карта", 1, object()])
def test_build_not_named_entity_raises_arguments_exception(source: object):
    """Источник, не являющийся сущностью с наименованием, отвергается."""
    # Подготовка
    report = TxtReport()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = report.build(source)  # pyright: ignore[reportArgumentType]


def test_build_range_outside_storage_returns_report():
    """Отчёт строится по любой сущности, а не только по лежащей в хранилище."""
    # Подготовка
    piece = RangeModel.create_piece()

    # Действие
    result = TxtReport().build(piece)

    # Проверка
    assert result.text.split("\n")[1] == "name: штука"
