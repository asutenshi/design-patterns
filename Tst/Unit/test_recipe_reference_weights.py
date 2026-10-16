import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.storage_manager import StorageManager
from Src.Models.abstract_recipe_item import AbstractRecipeItem
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nested_recipe_model import NestedRecipeModel
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


def make_recipe(result: NomenclatureModel, output_quantity: float, items: list[AbstractRecipeItem]) -> RecipeModel:
    """Создаёт карту с заданным результатом, выходом и составом."""
    return RecipeModel(result.name, result, output_quantity, 30, ["Шаг"], items)


def nested(recipe: RecipeModel, quantity: float, loss_ratio: float = 0) -> NestedRecipeModel:
    """Создаёт строку состава с вложенной картой."""
    return NestedRecipeModel(recipe, quantity, loss_ratio)


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


def test_weights_nested_recipe_changed_borscht_recalculated(first_start_storage: StorageManager):
    """Правка вложенной карты сразу меняет вес борща: соль 12 г убирается из бульона (выход 2000, строка 250 г)."""
    # Подготовка
    recipes = recipes_by_name(first_start_storage)
    salt = next(item for item in first_start_storage.nomenclatures if item.name == "Соль")
    borscht = recipes["Борщ с говядиной"]
    gross_before = borscht.gross_weight
    net_before = borscht.net_weight

    # Действие
    recipes["Бульон костный говяжий"].remove_item(salt)

    # Проверка
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
            nested(baked_bones, 800, 0.9),
            IngredientModel(make_nomenclature("Лук"), 100, 0.9),
            IngredientModel(make_nomenclature("Соль"), 12),
        ],
    )
    row = nested(bouillon, 250, 0.1)

    # Действие и проверка
    assert baked_bones.gross_weight == pytest.approx(1520)
    assert baked_bones.net_weight == pytest.approx(918)
    assert bouillon.gross_weight == pytest.approx(1328)
    assert bouillon.net_weight == pytest.approx(95.44)
    assert row.gross_weight == pytest.approx(166)
    assert row.net_weight == pytest.approx(10.737)


def test_add_item_cycle_through_chain_of_recipes_raises():
    """Карта A включает B, B включает C: добавление A в состав C замыкает цикл и бросает ArgumentsException."""
    # Подготовка
    a = make_recipe(make_nomenclature("A", NomenclatureType.DISH), 1, [])
    b = make_recipe(make_nomenclature("B", NomenclatureType.SEMI_FINISHED), 1, [])
    c = make_recipe(make_nomenclature("C", NomenclatureType.SEMI_FINISHED), 1, [])
    a.add_item(nested(b, 1))
    b.add_item(nested(c, 1))

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        c.add_item(nested(a, 1))
    assert c.items == []
