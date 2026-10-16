import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.abstract_recipe_item import AbstractRecipeItem
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nested_recipe_model import NestedRecipeModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def make_nomenclature(
    name: str = "Бульон", type: NomenclatureType = NomenclatureType.SEMI_FINISHED, grams_per_base_unit: float = 1
) -> NomenclatureModel:
    """Создаёт номенклатуру с заданными наименованием, типом и весом базовой единицы."""
    return NomenclatureModel(
        name,
        f"{name} (полное наименование)",
        NomenclatureGroupModel("Группа"),
        RangeModel("грамм", 1),
        type,
        grams_per_base_unit,
    )


def make_recipe(
    name: str = "Бульон", output_quantity: float = 200, items: list[AbstractRecipeItem] | None = None
) -> RecipeModel:
    """Создаёт карту полуфабриката: сырьё 400 г с потерями 0,5 даёт брутто 400 и нетто 200 при выходе 200."""
    if items is None:
        items = [IngredientModel(make_nomenclature("Кости", NomenclatureType.RAW_MATERIAL), 400, 0.5)]
    return RecipeModel(name, make_nomenclature(name), output_quantity, 30, ["Шаг"], items)


def test_init_valid_params_fields_set():
    """Вложенная карта сохраняет карту, количество и долю потерь; номенклатура — результат карты."""
    # Подготовка
    recipe = make_recipe()

    # Действие
    item = NestedRecipeModel(recipe, 50, 0.1)

    # Проверка
    assert item.recipe is recipe
    assert item.nomenclature is recipe.result
    assert item.quantity == 50
    assert item.loss_ratio == 0.1


def test_init_loss_ratio_omitted_defaults_to_zero():
    """Без доли потерь она равна нулю."""
    # Действие
    item = NestedRecipeModel(make_recipe(), 50)

    # Проверка
    assert item.loss_ratio == 0


def test_init_is_recipe_item():
    """Вложенная карта — элемент состава наравне с ингредиентом."""
    # Действие
    item = NestedRecipeModel(make_recipe(), 50)

    # Проверка
    assert isinstance(item, AbstractRecipeItem)


# Подготовка
@pytest.mark.parametrize("recipe", [None, "карта", 1, make_nomenclature()])
def test_init_not_recipe_raises(recipe):
    """Значение, не являющееся технологической картой, вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NestedRecipeModel(recipe, 50)


# Подготовка
@pytest.mark.parametrize("quantity", [0, -1, "10", None, True, float("nan"), float("inf")])
def test_init_invalid_quantity_raises(quantity):
    """Количество должно быть конечным числом больше нуля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NestedRecipeModel(make_recipe(), quantity)


# Подготовка
@pytest.mark.parametrize("loss_ratio", [-0.1, 1, 2, "0.1", None, True, float("nan")])
def test_init_invalid_loss_ratio_raises(loss_ratio):
    """Доля потерь должна лежать в промежутке [0, 1)."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NestedRecipeModel(make_recipe(), 50, loss_ratio)


def test_recipe_setter_not_allowed_raises():
    """Вложенную карту нельзя заменить: иначе в обход RecipeModel.add_item можно замкнуть цикл."""
    # Подготовка
    recipe = make_recipe()
    item = NestedRecipeModel(recipe, 50)

    # Действие и проверка
    with pytest.raises(AttributeError):
        item.recipe = make_recipe("Другой")  # pyright: ignore[reportAttributeAccessIssue]
    assert item.recipe is recipe


def test_setters_valid_values_updated_and_weights_recalculated():
    """Новое количество и потери сразу меняют веса: они принадлежат связи, а не карте."""
    # Подготовка
    item = NestedRecipeModel(make_recipe(), 50)

    # Действие
    item.quantity = 100
    item.loss_ratio = 0.5

    # Проверка
    assert item.quantity == 100
    assert item.loss_ratio == 0.5
    assert item.gross_weight == pytest.approx(200)
    assert item.net_weight == pytest.approx(50)


def test_gross_weight_proportional_to_recipe_output():
    """Брутто — вес брутто карты, умноженный на долю выхода: 400 * 50 / 200."""
    # Подготовка
    item = NestedRecipeModel(make_recipe(), 50)

    # Действие
    gross_weight = item.gross_weight

    # Проверка
    assert gross_weight == pytest.approx(100)


def test_net_weight_proportional_to_recipe_output_with_loss():
    """Нетто — вес нетто карты, умноженный на долю выхода и на (1 - потери): 200 * 100 / 200 * 0.9."""
    # Подготовка
    item = NestedRecipeModel(make_recipe(), 100, 0.1)

    # Действие
    net_weight = item.net_weight

    # Проверка
    assert net_weight == pytest.approx(90)


def test_weights_nested_recipe_changed_recalculated():
    """Веса не кешируются: правка вложенной карты сразу меняет вес элемента."""
    # Подготовка
    recipe = make_recipe()
    item = NestedRecipeModel(recipe, 200)

    # Действие
    recipe.add_item(IngredientModel(make_nomenclature("Соль", NomenclatureType.RAW_MATERIAL), 40))

    # Проверка
    assert item.gross_weight == pytest.approx(440)
    assert item.net_weight == pytest.approx(240)


def test_weights_nested_recipe_output_changed_recalculated():
    """Изменение выхода вложенной карты меняет долю, а значит и вес элемента."""
    # Подготовка
    recipe = make_recipe()
    item = NestedRecipeModel(recipe, 100)

    # Действие
    recipe.output_quantity = 400

    # Проверка
    assert item.gross_weight == pytest.approx(100)


def test_weights_nested_in_several_recipes_share_live_reference():
    """Одна карта входит в разные карты в разном количестве и по общей ссылке."""
    # Подготовка
    recipe = make_recipe()
    first = NestedRecipeModel(recipe, 50)
    second = NestedRecipeModel(recipe, 100, 0.5)

    # Действие
    recipe.output_quantity = 100

    # Проверка
    assert first.recipe is second.recipe
    assert first.gross_weight == pytest.approx(200)
    assert second.net_weight == pytest.approx(100)


def test_nomenclature_key_returns_result_id():
    """Ключ вложенной карты в составе — идентификатор результата карты."""
    # Подготовка
    recipe = make_recipe()
    item = NestedRecipeModel(recipe, 50)

    # Действие и проверка
    assert item.nomenclature_key() == recipe.result.id


def test_depends_on_recipe_result_returns_true():
    """Элемент зависит от номенклатуры, которая является результатом вложенной карты."""
    # Подготовка
    recipe = make_recipe()

    # Действие и проверка
    assert NestedRecipeModel(recipe, 50).depends_on(recipe.result) is True


def test_depends_on_ingredient_of_recipe_returns_true():
    """Элемент зависит от номенклатуры ингредиента вложенной карты."""
    # Подготовка
    bones = make_nomenclature("Кости", NomenclatureType.RAW_MATERIAL)
    recipe = make_recipe(items=[IngredientModel(bones, 400)])

    # Действие и проверка
    assert NestedRecipeModel(recipe, 50).depends_on(bones) is True


def test_depends_on_deeply_nested_recipe_result_returns_true():
    """Элемент зависит от результата карты, лежащей на несколько уровней глубже."""
    # Подготовка
    inner = make_recipe("Кости запечённые")
    middle = make_recipe("Бульон", items=[NestedRecipeModel(inner, 100)])
    outer = make_recipe("Суп", items=[NestedRecipeModel(middle, 100)])

    # Действие и проверка
    assert NestedRecipeModel(outer, 10).depends_on(inner.result) is True


def test_depends_on_unrelated_nomenclature_returns_false():
    """Элемент не зависит от номенклатуры, которой нет ни в карте, ни в её вложенных картах."""
    # Подготовка
    recipe = make_recipe(items=[NestedRecipeModel(make_recipe("Кости запечённые"), 100)])

    # Действие и проверка
    assert NestedRecipeModel(recipe, 50).depends_on(make_nomenclature("Соль")) is False


def test_add_item_recipe_with_same_result_raises():
    """Карта не может включать вложенную карту с тем же результатом, даже если это другой объект карты."""
    # Подготовка
    result = make_nomenclature("Суп", NomenclatureType.DISH)
    soup = RecipeModel("Суп", result, 500, 30, ["Шаг"])
    same_result = RecipeModel("Суп (вариант)", result, 500, 30, ["Шаг"])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        soup.add_item(NestedRecipeModel(same_result, 100))
    assert soup.items == []


def test_add_item_recipe_itself_raises():
    """Карта не может включать саму себя."""
    # Подготовка
    soup = make_recipe("Суп", items=[])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        soup.add_item(NestedRecipeModel(soup, 100))
    assert soup.items == []


def test_add_item_cycle_through_two_recipes_raises_and_keeps_composition():
    """A включает B, B включает A: второе добавление замыкает цикл и не меняет состав."""
    # Подготовка
    a = make_recipe("A", items=[])
    b = make_recipe("B", items=[])
    a.add_item(NestedRecipeModel(b, 1))

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        b.add_item(NestedRecipeModel(a, 1))
    assert b.items == []


def test_add_item_same_nested_recipe_twice_raises():
    """Одна карта входит в состав один раз: ключ уникальности — номенклатура результата."""
    # Подготовка
    recipe = make_recipe()
    soup = make_recipe("Суп", items=[NestedRecipeModel(recipe, 50)])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        soup.add_item(NestedRecipeModel(recipe, 100))
    assert len(soup.items) == 1


def test_remove_item_nested_recipe_by_result_removed():
    """Вложенная карта удаляется по номенклатуре её результата, как и ингредиент."""
    # Подготовка
    recipe = make_recipe()
    soup = make_recipe("Суп", items=[NestedRecipeModel(recipe, 50)])

    # Действие
    soup.remove_item(recipe.result)

    # Проверка
    assert soup.items == []
    assert soup.gross_weight == 0
