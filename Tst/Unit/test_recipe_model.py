import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_catalog import NomenclatureCatalog
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def make_nomenclature(
    name: str = "Картофель",
    type: NomenclatureType = NomenclatureType.RAW_MATERIAL,
    grams_per_base_unit: float = 1,
) -> NomenclatureModel:
    """Создаёт номенклатуру с заданными наименованием, типом и весом базовой единицы."""
    return NomenclatureModel(
        name,
        f"{name} (полное наименование)",
        NomenclatureGroupModel("Овощи"),
        RangeModel("грамм", 1),
        type,
        grams_per_base_unit,
    )


def make_result(type: NomenclatureType = NomenclatureType.SEMI_FINISHED) -> NomenclatureModel:
    """Создаёт номенклатуру-результат карты."""
    return make_nomenclature("Зажарка свекольная", type)


def make_ingredient(
    name: str = "Свёкла", quantity: float = 100, loss_ratio: float = 0, grams_per_base_unit: float = 1
) -> IngredientModel:
    """Создаёт ингредиент с новой номенклатурой."""
    return IngredientModel(make_nomenclature(name, grams_per_base_unit=grams_per_base_unit), quantity, loss_ratio)


def make_recipe(**overrides) -> RecipeModel:
    """Создаёт карту с корректными данными, подменяя переданные параметры."""
    params = {
        "name": "Зажарка свекольная",
        "result": make_result(),
        "output_quantity": 700,
        "cooking_time_minutes": 30,
        "steps": ["Нарезать овощи", "Обжарить"],
    }
    params.update(overrides)
    return RecipeModel(**params)


def test_init_valid_params_fields_set():
    """Карта создаётся с переданными значениями полей, пустым составом и заданным идентификатором."""
    # Подготовка
    result = make_result()

    # Действие
    recipe = RecipeModel("Зажарка", result, 700, 30, ["Нарезать овощи", "Обжарить"])

    # Проверка
    assert recipe.name == "Зажарка"
    assert recipe.result is result
    assert recipe.output_quantity == 700
    assert recipe.cooking_time_minutes == 30
    assert recipe.steps == ["Нарезать овощи", "Обжарить"]
    assert recipe.items == []
    assert recipe.id is not None


def test_init_items_passed_added_in_order():
    """Переданные в конструктор ингредиенты входят в состав в порядке передачи."""
    # Подготовка
    beet = make_ingredient("Свёкла")
    carrot = make_ingredient("Морковь")

    # Действие
    recipe = make_recipe(items=[beet, carrot])

    # Проверка
    assert recipe.items == [beet, carrot]


def test_init_duplicate_nomenclature_in_items_raises():
    """Две строки с одной номенклатурой в переданном составе вызывают ArgumentsException."""
    # Подготовка
    nomenclature = make_nomenclature("Свёкла")
    ingredients = [IngredientModel(nomenclature, 100), IngredientModel(nomenclature, 50)]

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(items=ingredients)


# Подготовка
@pytest.mark.parametrize("result_type", [NomenclatureType.SEMI_FINISHED, NomenclatureType.DISH])
def test_init_result_type_allowed_created(result_type: NomenclatureType):
    """Результатом карты может быть полуфабрикат или блюдо."""
    # Подготовка
    result = make_result(result_type)

    # Действие
    recipe = make_recipe(result=result)

    # Проверка
    assert recipe.result is result


# Подготовка
@pytest.mark.parametrize(
    "result_type", [NomenclatureType.RAW_MATERIAL, NomenclatureType.PRODUCT, NomenclatureType.PACKAGING]
)
def test_init_result_type_not_allowed_raises(result_type: NomenclatureType):
    """Сырьё, товар и упаковку нельзя сделать результатом карты."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(result=make_result(result_type))


# Подготовка
@pytest.mark.parametrize("result", [None, "Зажарка", NomenclatureGroupModel("Овощи")])
def test_init_result_not_nomenclature_raises(result):
    """Значение, не являющееся номенклатурой, в качестве результата вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(result=result)


# Подготовка
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None, "700"])
def test_init_invalid_output_quantity_raises(value):
    """Нулевой, отрицательный, нечисловой, bool, NaN или бесконечный выход вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(output_quantity=value)


# Подготовка
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None, "30"])
def test_init_invalid_cooking_time_raises(value):
    """Нулевое, отрицательное, нечисловое, bool, NaN или бесконечное время вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(cooking_time_minutes=value)


# Подготовка
@pytest.mark.parametrize("steps", ["Обжарить", None, [], [""], ["   "], [1], ["Нарезать", None], ("Обжарить",)])
def test_init_invalid_steps_raises(steps):
    """Не список, пустой список, нестроковый или пустой шаг вызывают ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(steps=steps)


def test_init_empty_name_raises():
    """Пустое наименование карты вызывает ArgumentsException (проверяет NamedEntity)."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(name="")


def test_steps_surrounding_spaces_stripped():
    """Пробелы по краям шагов отбрасываются."""
    # Действие
    recipe = make_recipe(steps=["  Нарезать овощи  ", "Обжарить"])

    # Проверка
    assert recipe.steps == ["Нарезать овощи", "Обжарить"]


def test_steps_source_list_changed_recipe_unchanged():
    """Изменение переданного списка шагов после создания не меняет карту."""
    # Подготовка
    steps = ["Нарезать овощи", "Обжарить"]
    recipe = make_recipe(steps=steps)

    # Действие
    steps.append("Подать")

    # Проверка
    assert recipe.steps == ["Нарезать овощи", "Обжарить"]


def test_steps_returned_list_changed_recipe_unchanged():
    """Изменение возвращённого списка шагов не меняет карту."""
    # Подготовка
    recipe = make_recipe()

    # Действие
    recipe.steps.append("Подать")

    # Проверка
    assert recipe.steps == ["Нарезать овощи", "Обжарить"]


def test_items_returned_list_changed_recipe_unchanged():
    """Изменение возвращённого списка ингредиентов не меняет состав карты."""
    # Подготовка
    recipe = make_recipe(items=[make_ingredient("Свёкла")])

    # Действие
    recipe.items.clear()

    # Проверка
    assert len(recipe.items) == 1


def test_setters_valid_values_updated():
    """Сеттеры обновляют наименование, выход, время и шаги."""
    # Подготовка
    recipe = make_recipe()

    # Действие
    recipe.name = "Зажарка новая"
    recipe.output_quantity = 800
    recipe.cooking_time_minutes = 45
    recipe.steps = ["Новый шаг"]

    # Проверка
    assert recipe.name == "Зажарка новая"
    assert recipe.output_quantity == 800
    assert recipe.cooking_time_minutes == 45
    assert recipe.steps == ["Новый шаг"]


# Подготовка
@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("output_quantity", 0),
        ("output_quantity", None),
        ("cooking_time_minutes", -5),
        ("cooking_time_minutes", True),
        ("steps", []),
        ("steps", "Обжарить"),
        ("steps", ["Нарезать", ""]),
    ],
)
def test_setters_invalid_value_raises_and_keeps_old(attribute, value):
    """Некорректное значение в сеттере вызывает ArgumentsException и не меняет прежнее значение."""
    # Подготовка
    recipe = make_recipe()
    old_value = getattr(recipe, attribute)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        setattr(recipe, attribute, value)
    assert getattr(recipe, attribute) == old_value


def test_result_setter_not_allowed_raises():
    """Результат карты нельзя заменить: он задаётся только в конструкторе."""
    # Подготовка
    recipe = make_recipe()

    # Действие и проверка
    with pytest.raises(AttributeError):
        recipe.result = make_result()  # pyright: ignore[reportAttributeAccessIssue]


def test_add_item_new_nomenclature_added():
    """Ингредиент с новой номенклатурой добавляется в состав в конец."""
    # Подготовка
    recipe = make_recipe(items=[make_ingredient("Свёкла")])
    carrot = make_ingredient("Морковь")

    # Действие
    recipe.add_item(carrot)

    # Проверка
    assert recipe.items[-1] is carrot
    assert len(recipe.items) == 2


def test_add_item_same_nomenclature_raises_and_keeps_composition():
    """Ингредиент с уже имеющейся номенклатурой отклоняется, состав не меняется."""
    # Подготовка
    nomenclature = make_nomenclature("Свёкла")
    first = IngredientModel(nomenclature, 100)
    recipe = make_recipe(items=[first])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.add_item(IngredientModel(nomenclature, 50))
    assert recipe.items == [first]


# Подготовка
@pytest.mark.parametrize("ingredient", [None, "Свёкла", make_nomenclature("Свёкла")])
def test_add_item_not_ingredient_raises(ingredient):
    """Значение, не являющееся ингредиентом, вызывает ArgumentsException."""
    # Подготовка
    recipe = make_recipe()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.add_item(ingredient)


def test_add_item_result_of_recipe_raises():
    """Результат карты нельзя добавить ингредиентом этой же карты."""
    # Подготовка
    result = make_result()
    recipe = make_recipe(result=result)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.add_item(IngredientModel(result, 100))
    assert recipe.items == []


def test_init_result_among_items_raises():
    """Результат карты среди переданных в конструктор ингредиентов вызывает ArgumentsException."""
    # Подготовка
    result = make_result()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_recipe(result=result, items=[IngredientModel(result, 100)])


def test_remove_item_existing_nomenclature_removed_and_order_kept():
    """Удаление по номенклатуре убирает ингредиент, порядок остальных сохраняется."""
    # Подготовка
    beet = make_ingredient("Свёкла")
    carrot = make_ingredient("Морковь")
    onion = make_ingredient("Лук")
    recipe = make_recipe(items=[beet, carrot, onion])

    # Действие
    recipe.remove_item(carrot.nomenclature)

    # Проверка
    assert recipe.items == [beet, onion]


def test_remove_item_missing_nomenclature_raises_and_keeps_composition():
    """Удаление номенклатуры, которой нет в составе, вызывает ArgumentsException."""
    # Подготовка
    beet = make_ingredient("Свёкла")
    recipe = make_recipe(items=[beet])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.remove_item(make_nomenclature("Морковь"))
    assert recipe.items == [beet]


# Подготовка
@pytest.mark.parametrize("nomenclature", [None, "Свёкла", NomenclatureGroupModel("Овощи")])
def test_remove_item_not_nomenclature_raises(nomenclature):
    """Значение, не являющееся номенклатурой, вызывает ArgumentsException."""
    # Подготовка
    recipe = make_recipe(items=[make_ingredient("Свёкла")])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.remove_item(nomenclature)


def test_remove_item_then_add_same_nomenclature_allowed():
    """После удаления номенклатуру можно добавить снова с другим количеством."""
    # Подготовка
    nomenclature = make_nomenclature("Свёкла")
    recipe = make_recipe(items=[IngredientModel(nomenclature, 100)])
    recipe.remove_item(nomenclature)

    # Действие
    recipe.add_item(IngredientModel(nomenclature, 250))

    # Проверка
    assert [item.quantity for item in recipe.items] == [250]


def test_weights_empty_recipe_are_zero():
    """У карты без ингредиентов веса брутто и нетто равны нулю."""
    # Подготовка
    recipe = make_recipe()

    # Действие и проверка
    assert recipe.gross_weight == 0
    assert recipe.net_weight == 0


def test_weights_several_items_summed():
    """Брутто и нетто карты — суммы брутто и нетто её ингредиентов."""
    # Подготовка
    recipe = make_recipe(
        items=[
            make_ingredient("Свёкла", 400, 0.2),  # брутто 400, нетто 320
            make_ingredient("Масло", 40, 0.1, grams_per_base_unit=0.92),  # брутто 36,8, нетто 33,12
            make_ingredient("Соль", 5),  # брутто 5, нетто 5
        ]
    )

    # Действие
    gross_weight = recipe.gross_weight
    net_weight = recipe.net_weight

    # Проверка
    assert gross_weight == pytest.approx(441.8)
    assert net_weight == pytest.approx(358.12)


def test_weights_ingredient_added_recalculated():
    """После добавления ингредиента брутто и нетто увеличиваются на его веса."""
    # Подготовка
    recipe = make_recipe(items=[make_ingredient("Свёкла", 400, 0.2)])

    # Действие
    recipe.add_item(make_ingredient("Морковь", 100, 0.5))

    # Проверка
    assert recipe.gross_weight == pytest.approx(500)
    assert recipe.net_weight == pytest.approx(370)


def test_weights_ingredient_removed_recalculated():
    """После исключения ингредиента брутто и нетто уменьшаются на его веса."""
    # Подготовка
    beet = make_ingredient("Свёкла", 400, 0.2)
    carrot = make_ingredient("Морковь", 100, 0.5)
    recipe = make_recipe(items=[beet, carrot])

    # Действие
    recipe.remove_item(carrot.nomenclature)

    # Проверка
    assert recipe.gross_weight == pytest.approx(400)
    assert recipe.net_weight == pytest.approx(320)


def test_weights_last_ingredient_removed_are_zero():
    """После исключения последнего ингредиента веса брутто и нетто равны нулю."""
    # Подготовка
    beet = make_ingredient("Свёкла", 400, 0.2)
    recipe = make_recipe(items=[beet])

    # Действие
    recipe.remove_item(beet.nomenclature)

    # Проверка
    assert recipe.gross_weight == 0
    assert recipe.net_weight == 0


def test_weights_ingredient_changed_in_recipe_recalculated():
    """Изменение количества и потерь у ингредиента, уже лежащего в карте, меняет веса карты."""
    # Подготовка
    beet = make_ingredient("Свёкла", 400, 0.2)
    recipe = make_recipe(items=[beet])

    # Действие
    beet.quantity = 500
    beet.loss_ratio = 0.4

    # Проверка
    assert recipe.gross_weight == pytest.approx(500)
    assert recipe.net_weight == pytest.approx(300)


def test_weights_packaging_counted_in_gross_and_net():
    """Упаковка — такой же ингредиент: её вес входит и в брутто, и в нетто (потери упаковки — 0)."""
    # Подготовка
    container = IngredientModel(make_nomenclature("Контейнер", NomenclatureType.PACKAGING, 20), 1)
    recipe = make_recipe(result=make_result(NomenclatureType.DISH), items=[container])

    # Действие и проверка
    assert recipe.gross_weight == pytest.approx(20)
    assert recipe.net_weight == pytest.approx(20)


def test_result_key_returns_result_id():
    """Ключ карты в хранилище — идентификатор номенклатуры-результата."""
    # Подготовка
    result = make_result()
    recipe = make_recipe(result=result)

    # Действие
    key = recipe.result_key()

    # Проверка
    assert key == result.id


def test_result_key_same_result_keys_equal():
    """Две карты одного результата дают один ключ, поэтому в хранилище вторая карта на позицию не пройдёт."""
    # Подготовка
    result = make_result()
    first = make_recipe(name="Зажарка", result=result)
    second = make_recipe(name="Зажарка другая", result=result)

    # Действие и проверка
    assert first.result_key() == second.result_key()


def test_gross_weight_for_scales_proportionally():
    """Масштабирование брутто: для выхода 200 г при базовом 400 г вес уменьшается вдвое."""
    # Подготовка
    raw = make_ingredient("Мясо", quantity=400)
    recipe = make_recipe(output_quantity=400, items=[raw])

    # Действие
    scaled = recipe.gross_weight_for(200)

    # Проверка
    assert scaled == pytest.approx(200)


def test_net_weight_for_scales_proportionally():
    """Масштабирование нетто: для выхода 600 г при базовом 400 г вес увеличивается в 1,5 раза."""
    # Подготовка
    raw = make_ingredient("Мясо", quantity=400, loss_ratio=0.25)
    recipe = make_recipe(output_quantity=400, items=[raw])

    # Действие
    scaled = recipe.net_weight_for(600)

    # Проверка
    assert scaled == pytest.approx(450)


# Подготовка
@pytest.mark.parametrize("method_name", ["gross_weight_for", "net_weight_for"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None, "200"])
def test_weights_for_invalid_output_raises(method_name, value):
    """Нулевой, отрицательный, нечисловой, bool, NaN и бесконечный выход вызывает ArgumentsException."""
    # Подготовка
    recipe = make_recipe()
    method = getattr(recipe, method_name)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        method(value)


def make_bouillon_recipe(output_quantity: float = 200) -> RecipeModel:
    """Создаёт карту бульона: кости 400 г с потерями 0,5 дают брутто 400 и нетто 200."""
    return RecipeModel(
        "Бульон",
        make_nomenclature("Бульон", NomenclatureType.SEMI_FINISHED),
        output_quantity,
        60,
        ["Шаг"],
        [IngredientModel(make_nomenclature("Кости"), 400, 0.5)],
    )


def test_as_ingredient_valid_params_fields_set():
    """Строка из карты: номенклатура — результат карты, количество и потери — переданные."""
    # Подготовка
    recipe = make_bouillon_recipe()

    # Действие
    ingredient = recipe.as_ingredient(50, 0.1)

    # Проверка
    assert ingredient.nomenclature is recipe.result
    assert ingredient.quantity == 50
    assert ingredient.loss_ratio == 0.1


def test_as_ingredient_loss_ratio_omitted_defaults_to_zero():
    """Без доли потерь она равна нулю."""
    # Действие
    ingredient = make_bouillon_recipe().as_ingredient(50)

    # Проверка
    assert ingredient.loss_ratio == 0


def test_as_ingredient_base_scaled_by_output():
    """Основание — состав карты, умноженный на долю выхода: кости 400 * 50 / 200."""
    # Подготовка
    recipe = make_bouillon_recipe()

    # Действие
    ingredient = recipe.as_ingredient(50)

    # Проверка
    assert [item.nomenclature for item in ingredient.base] == [item.nomenclature for item in recipe.items]
    assert ingredient.base[0].quantity == pytest.approx(100)
    assert recipe.items[0].quantity == 400


def test_as_ingredient_weights_proportional_to_output_with_loss():
    """Брутто — брутто карты по доле выхода, нетто — ещё и за вычетом потерь строки: 200 * 100 / 200 * 0.9."""
    # Подготовка
    recipe = make_bouillon_recipe()

    # Действие
    ingredient = recipe.as_ingredient(100, 0.1)

    # Проверка
    assert ingredient.gross_weight == pytest.approx(recipe.gross_weight_for(100))
    assert ingredient.gross_weight == pytest.approx(200)
    assert ingredient.net_weight == pytest.approx(90)


def test_as_ingredient_two_level_nesting_scaled_on_each_level():
    """Полуфабрикат из полуфабриката: масштаб применяется на каждом уровне."""
    # Подготовка
    soup = RecipeModel(
        "Суп",
        make_nomenclature("Суп", NomenclatureType.DISH),
        1000,
        30,
        ["Шаг"],
        [make_bouillon_recipe().as_ingredient(400, 0.1), make_ingredient("Картофель", 200, 0.5)],
    )

    # Действие
    ingredient = soup.as_ingredient(500)

    # Проверка
    bouillon = ingredient.base[0]
    assert bouillon.quantity == pytest.approx(200)
    assert bouillon.base[0].quantity == pytest.approx(400)
    assert ingredient.gross_weight == pytest.approx(500)
    # Нетто супа: бульон (800 * 0.5) * 0.9 = 360 и картофель 200 * 0.5 = 100, выход 500 из 1000
    assert ingredient.net_weight == pytest.approx((360 + 100) / 2)


def test_as_ingredient_recipe_changed_snapshot_unchanged():
    """Строка — снимок: правка карты не меняет уже собранную строку, её нужно собрать заново."""
    # Подготовка
    recipe = make_bouillon_recipe()
    ingredient = recipe.as_ingredient(200)

    # Действие
    recipe.add_item(make_ingredient("Соль", 40))
    recipe.output_quantity = 400

    # Проверка
    assert ingredient.gross_weight == pytest.approx(400)
    assert recipe.as_ingredient(200).gross_weight == pytest.approx(220)


def test_as_ingredient_several_snapshots_independent():
    """Одна карта даёт независимые строки для разных карт: у каждой своё количество и основание."""
    # Подготовка
    recipe = make_bouillon_recipe()
    first = recipe.as_ingredient(50)
    second = recipe.as_ingredient(100, 0.5)

    # Действие
    first.quantity = 200

    # Проверка
    assert first.gross_weight == pytest.approx(400)
    assert second.gross_weight == pytest.approx(200)
    assert second.net_weight == pytest.approx(50)


def test_as_ingredient_empty_recipe_gives_leaf():
    """Из карты без состава получается строка без основания: её вес считается как у сырья."""
    # Подготовка
    recipe = make_recipe(result=make_nomenclature("Соус", NomenclatureType.SEMI_FINISHED, grams_per_base_unit=2))

    # Действие
    ingredient = recipe.as_ingredient(50)

    # Проверка
    assert ingredient.base == ()
    assert ingredient.gross_weight == pytest.approx(100)


# Подготовка
@pytest.mark.parametrize(("quantity", "loss_ratio"), [(0, 0), (-1, 0), ("10", 0), (None, 0), (True, 0), (50, 1), (50, -0.1)])
def test_as_ingredient_invalid_params_raises(quantity, loss_ratio):
    """Количество должно быть больше нуля, доля потерь — в промежутке [0, 1)."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_bouillon_recipe().as_ingredient(quantity, loss_ratio)


def test_add_item_snapshot_of_itself_raises():
    """Карта не может включить снимок самой себя или другой карты с тем же результатом."""
    # Подготовка
    recipe = make_bouillon_recipe()
    same_result = RecipeModel("Бульон (вариант)", recipe.result, 500, 30, ["Шаг"], [make_ingredient("Вода", 500)])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        recipe.add_item(recipe.as_ingredient(100))
    with pytest.raises(ArgumentsException):
        recipe.add_item(same_result.as_ingredient(100))
    assert len(recipe.items) == 1


def test_add_item_result_in_base_raises_and_keeps_composition():
    """Результат карты в основании добавляемой строки (цикл через другую карту) бросает ArgumentsException."""
    # Подготовка
    soup = RecipeModel("Суп", make_nomenclature("Суп", NomenclatureType.DISH), 500, 30, ["Шаг"])
    bouillon = make_bouillon_recipe()
    bouillon.add_item(soup.as_ingredient(1))
    soup_items_before = soup.items

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        soup.add_item(bouillon.as_ingredient(300))
    assert soup.items == soup_items_before


def test_add_item_same_semi_finished_twice_raises():
    """Полуфабрикат входит в состав один раз: ключ уникальности — номенклатура результата."""
    # Подготовка
    recipe = make_bouillon_recipe()
    soup = RecipeModel(
        "Суп", make_nomenclature("Суп", NomenclatureType.DISH), 500, 30, ["Шаг"], [recipe.as_ingredient(50)]
    )

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        soup.add_item(recipe.as_ingredient(100))
    assert len(soup.items) == 1


def test_remove_item_semi_finished_by_result_removed():
    """Полуфабрикат удаляется по номенклатуре результата его карты, как и сырьё."""
    # Подготовка
    recipe = make_bouillon_recipe()
    soup = RecipeModel(
        "Суп", make_nomenclature("Суп", NomenclatureType.DISH), 500, 30, ["Шаг"], [recipe.as_ingredient(50)]
    )

    # Действие
    soup.remove_item(recipe.result)

    # Проверка
    assert soup.items == []
    assert soup.gross_weight == 0


# Номенклатура, отличающаяся от «сырья весом 1 г на базовую единицу»: тип и вес базовой единицы
SPECIAL_NOMENCLATURE = {
    "Бульон костный говяжий": (NomenclatureType.SEMI_FINISHED, 1),
    "Говядина отварная": (NomenclatureType.SEMI_FINISHED, 1),
    "Зажарка свекольная": (NomenclatureType.SEMI_FINISHED, 1),
    "Борщ с говядиной": (NomenclatureType.DISH, 500),
    "Лавровый лист": (NomenclatureType.RAW_MATERIAL, 0.5),
    "Масло подсолнечное": (NomenclatureType.RAW_MATERIAL, 0.92),
    "Контейнер для супа 500 мл": (NomenclatureType.PACKAGING, 20),
}
# Результат и ингредиенты каждой карты: именно эти наименования ищет фабрика в справочнике
BOUILLON_NAMES = (
    "Бульон костный говяжий",
    "Кости говяжьи мозговые",
    "Лук репчатый",
    "Морковь",
    "Лавровый лист",
    "Перец чёрный горошком",
    "Соль",
)
BOILED_BEEF_NAMES = ("Говядина отварная", "Говядина (мякоть)", "Лавровый лист", "Соль")
BEET_FRY_NAMES = (
    "Зажарка свекольная",
    "Свёкла",
    "Морковь",
    "Лук репчатый",
    "Томатная паста",
    "Масло подсолнечное",
    "Уксус 9%",
    "Сахар",
    "Соль",
)
BORSCHT_NAMES = (
    "Борщ с говядиной",
    "Бульон костный говяжий",
    "Говядина отварная",
    "Зажарка свекольная",
    "Картофель",
    "Капуста белокочанная",
    "Сметана 20%",
    "Укроп",
    "Контейнер для супа 500 мл",
)
# Всё, что нужно борщу вместе со своими полуфабрикатами, без повторов
ALL_NAMES = tuple(dict.fromkeys(BORSCHT_NAMES + BOUILLON_NAMES + BOILED_BEEF_NAMES + BEET_FRY_NAMES))


def make_catalog(*names: str) -> NomenclatureCatalog:
    """Создаёт справочник номенклатуры по наименованиям: особые позиции — из SPECIAL_NOMENCLATURE, остальные — сырьё по 1 г."""
    nomenclatures = []
    for name in names:
        type, grams_per_base_unit = SPECIAL_NOMENCLATURE.get(name, (NomenclatureType.RAW_MATERIAL, 1))
        nomenclatures.append(make_nomenclature(name, type, grams_per_base_unit))
    return NomenclatureCatalog(nomenclatures)


def test_create_beef_bouillon_full_catalog_fields_and_weights():
    """Карта бульона берёт результат из справочника, выход и время — из рецепта, веса считаются по потерям."""
    # Подготовка
    catalog = make_catalog(*BOUILLON_NAMES)

    # Действие
    recipe = RecipeModel.create_beef_bouillon(catalog)

    # Проверка
    assert recipe.name == "Бульон костный говяжий"
    assert recipe.result is catalog.get("Бульон костный говяжий")
    assert recipe.output_quantity == 2000
    assert recipe.cooking_time_minutes == 240
    assert len(recipe.steps) == 6
    assert [i.nomenclature.name for i in recipe.items] == list(BOUILLON_NAMES[1:])
    assert [i.quantity for i in recipe.items] == [1500, 100, 80, 1, 3, 12]
    assert recipe.gross_weight == pytest.approx(1695.5)
    assert recipe.net_weight == pytest.approx(180.35)


def test_create_boiled_beef_full_catalog_fields_and_weights():
    """Карта отварной говядины: нетто совпадает с выходом 500 г, потери берутся из ингредиентов."""
    # Подготовка
    catalog = make_catalog(*BOILED_BEEF_NAMES)

    # Действие
    recipe = RecipeModel.create_boiled_beef(catalog)

    # Проверка
    assert recipe.name == "Говядина отварная"
    assert recipe.result is catalog.get("Говядина отварная")
    assert recipe.output_quantity == 500
    assert recipe.cooking_time_minutes == 120
    assert len(recipe.steps) == 4
    assert [i.nomenclature.name for i in recipe.items] == list(BOILED_BEEF_NAMES[1:])
    assert recipe.gross_weight == pytest.approx(808.5)
    assert recipe.net_weight == pytest.approx(500.05)


def test_create_beet_fry_full_catalog_fields_and_weights():
    """Карта зажарки: масло переводится из миллилитров в граммы по плотности, нетто около выхода 700 г."""
    # Подготовка
    catalog = make_catalog(*BEET_FRY_NAMES)

    # Действие
    recipe = RecipeModel.create_beet_fry(catalog)

    # Проверка
    assert recipe.name == "Зажарка свекольная"
    assert recipe.result is catalog.get("Зажарка свекольная")
    assert recipe.output_quantity == 700
    assert recipe.cooking_time_minutes == 30
    assert len(recipe.steps) == 5
    assert [i.nomenclature.name for i in recipe.items] == list(BEET_FRY_NAMES[1:])
    assert recipe.gross_weight == pytest.approx(751.8)
    assert recipe.net_weight == pytest.approx(700.12)


def test_create_borscht_full_catalog_semi_finished_and_packaging_in_composition():
    """Карта борща включает три полуфабриката и упаковку, ссылаясь на объекты справочника; результата в составе нет."""
    # Подготовка
    catalog = make_catalog(*ALL_NAMES)

    # Действие
    recipe = RecipeModel.create_borscht(catalog)

    # Проверка
    nomenclatures = [i.nomenclature for i in recipe.items]
    assert recipe.name == "Борщ с говядиной"
    assert recipe.result is catalog.get("Борщ с говядиной")
    assert recipe.output_quantity == 1
    assert recipe.cooking_time_minutes == 15
    assert len(recipe.steps) == 4
    assert len(nomenclatures) == len(BORSCHT_NAMES) - 1
    assert all(a is catalog.get(name) for a, name in zip(nomenclatures, BORSCHT_NAMES[1:], strict=True))
    assert recipe.result not in nomenclatures
    assert [n.type for n in nomenclatures].count(NomenclatureType.SEMI_FINISHED) == 3
    assert NomenclatureType.PACKAGING in [n.type for n in nomenclatures]


def test_create_borscht_without_recipes_builds_them_from_catalog():
    """Не переданные карты полуфабрикатов создаются из справочника и входят в состав снимками с основанием."""
    # Подготовка
    catalog = make_catalog(*ALL_NAMES)

    # Действие
    recipe = RecipeModel.create_borscht(catalog)

    # Проверка
    composite = {i.nomenclature.name: i for i in recipe.items if i.base}
    assert set(composite) == {"Бульон костный говяжий", "Говядина отварная", "Зажарка свекольная"}
    for name, item in composite.items():
        assert item.nomenclature is catalog.get(name)


def test_create_borscht_passed_recipes_used_for_snapshots():
    """Строки полуфабрикатов собраны из переданных карт: состав и вес совпадают с картой по доле выхода."""
    # Подготовка
    catalog = make_catalog(*ALL_NAMES)
    bouillon = RecipeModel.create_beef_bouillon(catalog)
    boiled_beef = RecipeModel.create_boiled_beef(catalog)
    beet_fry = RecipeModel.create_beet_fry(catalog)

    # Действие
    recipe = RecipeModel.create_borscht(catalog, bouillon, boiled_beef, beet_fry)

    # Проверка
    by_result = {i.nomenclature: i for i in recipe.items}
    for source in (bouillon, boiled_beef, beet_fry):
        item = by_result[source.result]
        assert [b.nomenclature for b in item.base] == [i.nomenclature for i in source.items]
        assert item.gross_weight == pytest.approx(source.gross_weight_for(item.quantity))


def test_create_borscht_full_catalog_weights_include_packaging():
    """Брутто 577.14 г и нетто 314.31 г считаются рекурсивно и включают контейнер (20 г)."""
    # Подготовка
    catalog = make_catalog(*ALL_NAMES)

    # Действие
    recipe = RecipeModel.create_borscht(catalog)

    # Проверка
    assert recipe.gross_weight == pytest.approx(577.1375)
    assert recipe.net_weight == pytest.approx(314.306475)
    recipe.remove_item(catalog.get("Контейнер для супа 500 мл"))
    assert recipe.gross_weight == pytest.approx(557.1375)
    assert recipe.net_weight == pytest.approx(294.306475)
    assert recipe.output_quantity * recipe.result.grams_per_base_unit == 500


def test_create_borscht_with_recipes_calculates_recursive_weights():
    """С явно переданными картами брутто и нетто борща совпадают с расчётом по картам из справочника."""
    # Подготовка
    catalog = make_catalog(*ALL_NAMES)
    bouillon = RecipeModel.create_beef_bouillon(catalog)
    boiled_beef = RecipeModel.create_boiled_beef(catalog)
    beet_fry = RecipeModel.create_beet_fry(catalog)

    # Действие
    recipe = RecipeModel.create_borscht(catalog, bouillon, boiled_beef, beet_fry)

    # Проверка
    assert recipe.gross_weight == pytest.approx(577.1375)
    assert recipe.net_weight == pytest.approx(314.306475)


# Подготовка
@pytest.mark.parametrize(
    ("factory", "missing"),
    [
        pytest.param(factory, name, id=f"{factory.__name__}-{name}")
        for factory, names in (
            (RecipeModel.create_beef_bouillon, BOUILLON_NAMES),
            (RecipeModel.create_boiled_beef, BOILED_BEEF_NAMES),
            (RecipeModel.create_beet_fry, BEET_FRY_NAMES),
            (RecipeModel.create_borscht, ALL_NAMES),
        )
        for name in names
    ],
)
def test_create_recipe_missing_nomenclature_raises(factory, missing):
    """Если в справочнике нет результата или любого ингредиента, фабрика бросает ArgumentsException."""
    # Подготовка
    catalog = make_catalog(*(name for name in ALL_NAMES if name != missing))

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory(catalog)
