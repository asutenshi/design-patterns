import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel

# Эталонные веса карт из Recipes.md: (брутто, нетто) в граммах.
# Получены запуском кода до рефакторинга вложенных карт и обязаны сохраняться после него.
EXPECTED_RECIPE_WEIGHTS = {
    "Бульон костный говяжий": (1695.5, 180.35),
    "Говядина отварная": (808.5, 500.05),
    "Зажарка свекольная": (751.8, 700.12),
    "Борщ с говядиной": (577.1375, 314.306475),
}
# Эталонные веса строк состава борща: (брутто, нетто) в граммах
EXPECTED_BORSCHT_ROWS = {
    "Бульон костный говяжий": (211.9375, 20.289375),
    "Говядина отварная": (97.02, 57.0057),
    "Зажарка свекольная": (75.18, 66.5114),
    "Картофель": (80, 68),
    "Капуста белокочанная": (70, 59.5),
    "Сметана 20%": (20, 20),
    "Укроп": (3, 3),
    "Контейнер для супа 500 мл": (20, 20),
}


def make_nomenclature(name: str, type: NomenclatureType = NomenclatureType.RAW_MATERIAL) -> NomenclatureModel:
    """Создаёт номенклатуру с весом базовой единицы 1 г."""
    return NomenclatureModel(
        name, f"{name} (полное наименование)", NomenclatureGroupModel("Группа"), RangeModel("грамм", 1), type, 1
    )


def make_recipe(result: NomenclatureModel, output_quantity: float, items: list[IngredientModel]) -> RecipeModel:
    """Создаёт карту с заданным результатом, выходом и составом."""
    return RecipeModel(result.name, result, output_quantity, 30, ["Шаг"], items)


def recipes_by_name(storage: StorageManager) -> dict[str, RecipeModel]:
    """Возвращает карты хранилища по наименованию."""
    return {recipe.name: recipe for recipe in storage.recipes}


def test_weights_first_start_recipes_match_reference_values(first_start_storage: StorageManager):
    """Брутто и нетто четырёх карт первого запуска совпадают с эталонными значениями."""
    # Подготовка
    recipes = recipes_by_name(first_start_storage)

    # Действие
    actual = {name: (recipe.gross_weight, recipe.net_weight) for name, recipe in recipes.items()}

    # Проверка
    assert actual.keys() == EXPECTED_RECIPE_WEIGHTS.keys()
    for name, (gross, net) in EXPECTED_RECIPE_WEIGHTS.items():
        assert actual[name] == (pytest.approx(gross), pytest.approx(net)), name


def test_weights_borscht_rows_match_reference_values(first_start_storage: StorageManager):
    """Брутто и нетто каждой строки состава борща совпадают с эталонными значениями."""
    # Подготовка
    borscht = recipes_by_name(first_start_storage)["Борщ с говядиной"]

    # Действие
    actual = {row.nomenclature.name: (row.gross_weight, row.net_weight) for row in borscht.items}

    # Проверка
    assert actual.keys() == EXPECTED_BORSCHT_ROWS.keys()
    for name, (gross, net) in EXPECTED_BORSCHT_ROWS.items():
        assert actual[name] == (pytest.approx(gross), pytest.approx(net)), name


def test_weights_borscht_sum_of_rows_equals_recipe_weights(first_start_storage: StorageManager):
    """Вес борща равен сумме эталонных весов его строк."""
    # Подготовка
    borscht = recipes_by_name(first_start_storage)["Борщ с говядиной"]

    # Действие
    gross = sum(gross for gross, _ in EXPECTED_BORSCHT_ROWS.values())
    net = sum(net for _, net in EXPECTED_BORSCHT_ROWS.values())

    # Проверка
    assert borscht.gross_weight == pytest.approx(gross)
    assert borscht.net_weight == pytest.approx(net)


def test_weights_semi_finished_recipe_changed_assembled_borscht_unchanged(first_start_storage: StorageManager):
    """Правка карты бульона не меняет уже собранный борщ: строка бульона — снимок.

    Пересборка строки (в будущем её выполнит наблюдатель) учитывает правку: соль 12 г убирается из бульона
    с выходом 2000, строка 250 г с потерями 0,1.
    """
    # Подготовка
    recipes = recipes_by_name(first_start_storage)
    salt = next(item for item in first_start_storage.nomenclatures if item.name == "Соль")
    bouillon = recipes["Бульон костный говяжий"]
    borscht = recipes["Борщ с говядиной"]
    gross_before = borscht.gross_weight
    net_before = borscht.net_weight

    # Действие
    bouillon.remove_item(salt)
    gross_stale = borscht.gross_weight
    borscht.remove_item(bouillon.result)
    borscht.add_item(bouillon.as_ingredient(250, 0.1))

    # Проверка
    assert gross_stale == pytest.approx(gross_before)
    # 12 г соли без потерь, доля бульона в борще 250 / 2000 и потери строки 0,1
    assert borscht.gross_weight == pytest.approx(gross_before - 12 * 0.125)
    assert borscht.net_weight == pytest.approx(net_before - 12 * 0.125 * 0.9)


def test_weights_three_level_nesting_scaled_by_quantity_and_loss():
    """Три уровня вложенности: вес масштабируется выходом карты на каждом уровне, потери строки применяются к нетто."""
    # Подготовка
    baked_bones = make_recipe(
        make_nomenclature("Кости запечённые", NomenclatureType.SEMI_FINISHED),
        1000,
        [
            IngredientModel(make_nomenclature("Кости"), 1500, 0.4),
            IngredientModel(make_nomenclature("Масло"), 20, 0.1),
        ],
    )
    bouillon = make_recipe(
        make_nomenclature("Бульон", NomenclatureType.SEMI_FINISHED),
        2000,
        [
            baked_bones.as_ingredient(800, 0.9),
            IngredientModel(make_nomenclature("Лук"), 100, 0.9),
            IngredientModel(make_nomenclature("Соль"), 12),
        ],
    )
    row = bouillon.as_ingredient(250, 0.1)

    # Действие и проверка
    assert baked_bones.gross_weight == pytest.approx(1520)
    assert baked_bones.net_weight == pytest.approx(918)
    assert bouillon.gross_weight == pytest.approx(1328)
    assert bouillon.net_weight == pytest.approx(95.44)
    assert row.gross_weight == pytest.approx(166)
    assert row.net_weight == pytest.approx(10.737)


def test_add_item_cycle_through_chain_of_recipes_raises():
    """A включает снимок B, B — снимок C: снимок A в составе C замкнул бы цикл и бросает ArgumentsException.

    Карты собираются снизу вверх, поэтому снимки свежие и видят всю цепочку.
    """
    # Подготовка
    c = make_recipe(make_nomenclature("C", NomenclatureType.SEMI_FINISHED), 1, [])
    b = make_recipe(make_nomenclature("B", NomenclatureType.SEMI_FINISHED), 1, [c.as_ingredient(1)])
    a = make_recipe(make_nomenclature("A", NomenclatureType.DISH), 1, [b.as_ingredient(1)])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        c.add_item(a.as_ingredient(1))
    assert c.items == []
