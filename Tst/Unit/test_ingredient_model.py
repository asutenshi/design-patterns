import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel


def make_nomenclature(
    grams_per_base_unit: float = 1,
    range: RangeModel | None = None,
    type: NomenclatureType = NomenclatureType.RAW_MATERIAL,
) -> NomenclatureModel:
    """Создаёт номенклатуру с корректными данными, заданным типом и весом базовой единицы."""
    return NomenclatureModel(
        "Картофель",
        "Картофель свежий",
        NomenclatureGroupModel("Овощи"),
        range if range is not None else RangeModel("грамм", 1),
        type,
        grams_per_base_unit,
    )


def make_ingredient(**overrides) -> IngredientModel:
    """Создаёт ингредиент с корректными данными, подменяя переданные параметры."""
    params = {
        "nomenclature": make_nomenclature(),
        "quantity": 80,
        "loss_ratio": 0,
    }
    params.update(overrides)
    return IngredientModel(**params)


def test_init_valid_params_fields_set():
    """Ингредиент создаётся с переданными номенклатурой, количеством и долей потерь."""
    # Подготовка
    nomenclature = make_nomenclature()

    # Действие
    ingredient = IngredientModel(nomenclature, 80, 0.25)

    # Проверка
    assert ingredient.nomenclature is nomenclature
    assert ingredient.quantity == 80
    assert ingredient.loss_ratio == 0.25


def test_init_loss_ratio_omitted_defaults_to_zero():
    """Если доля потерь не указана, потерь нет."""
    # Действие
    ingredient = IngredientModel(make_nomenclature(), 80)

    # Проверка
    assert ingredient.loss_ratio == 0


# Подготовка
@pytest.mark.parametrize("nomenclature", [None, "Картофель", NomenclatureGroupModel("Овощи"), RangeModel("грамм", 1)])
def test_init_not_nomenclature_raises(nomenclature):
    """Значение, не являющееся номенклатурой, вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_ingredient(nomenclature=nomenclature)


# Подготовка
@pytest.mark.parametrize("quantity", [0, -1, -0.5, float("nan"), float("inf"), True, None, "80"])
def test_init_invalid_quantity_raises(quantity):
    """Нулевое, отрицательное, нечисловое, bool, NaN и бесконечное количество вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_ingredient(quantity=quantity)


# Подготовка
@pytest.mark.parametrize("loss_ratio", [-0.1, 1, 1.5, float("nan"), float("inf"), True, None, "0.1"])
def test_init_invalid_loss_ratio_raises(loss_ratio):
    """Доля потерь вне промежутка [0, 1), нечисловая, bool, NaN или бесконечная вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_ingredient(loss_ratio=loss_ratio)


# Подготовка
@pytest.mark.parametrize("loss_ratio", [0, 0.999])
def test_init_loss_ratio_boundaries_created(loss_ratio):
    """Граничные значения доли потерь (0 и почти 1) допустимы."""
    # Действие
    ingredient = make_ingredient(loss_ratio=loss_ratio)

    # Проверка
    assert ingredient.loss_ratio == loss_ratio


def test_setters_valid_values_updated():
    """Сеттеры обновляют количество и долю потерь."""
    # Подготовка
    ingredient = make_ingredient()

    # Действие
    ingredient.quantity = 120
    ingredient.loss_ratio = 0.4

    # Проверка
    assert ingredient.quantity == 120
    assert ingredient.loss_ratio == 0.4


# Подготовка
@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("quantity", 0),
        ("quantity", -1),
        ("quantity", None),
        ("quantity", True),
        ("loss_ratio", -0.1),
        ("loss_ratio", 1),
        ("loss_ratio", None),
        ("loss_ratio", True),
    ],
)
def test_setters_invalid_value_raises_and_keeps_old(attribute, value):
    """Некорректное значение в сеттере вызывает ArgumentsException и не меняет прежнее значение."""
    # Подготовка
    ingredient = make_ingredient(quantity=80, loss_ratio=0.25)
    old_value = getattr(ingredient, attribute)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        setattr(ingredient, attribute, value)
    assert getattr(ingredient, attribute) == old_value


def test_nomenclature_setter_not_allowed_raises():
    """Номенклатуру ингредиента нельзя заменить: она задаётся только в конструкторе."""
    # Подготовка
    ingredient = make_ingredient()

    # Действие и проверка
    with pytest.raises(AttributeError):
        ingredient.nomenclature = make_nomenclature()  # pyright: ignore[reportAttributeAccessIssue]


# Подготовка
@pytest.mark.parametrize(
    ("quantity", "grams_per_base_unit", "expected"),
    [
        (80, 1, 80),  # картофель, граммы
        (40, 0.92, 36.8),  # масло подсолнечное, миллилитры
        (1, 0.5, 0.5),  # лавровый лист, штука
        (1, 20, 20),  # контейнер для супа, штука
    ],
)
def test_gross_weight_quantity_in_base_unit_multiplied_by_unit_weight(quantity, grams_per_base_unit, expected):
    """Вес брутто равен количеству в базовой единице, умноженному на вес этой единицы в граммах."""
    # Подготовка
    ingredient = make_ingredient(
        nomenclature=make_nomenclature(grams_per_base_unit), quantity=quantity, loss_ratio=0.5
    )

    # Действие
    gross_weight = ingredient.gross_weight

    # Проверка
    assert gross_weight == pytest.approx(expected)


def test_gross_weight_kilogram_nomenclature_quantity_in_grams():
    """Для номенклатуры в килограммах количество задаётся в граммах (базовой единице): 800 — это 800 г."""
    # Подготовка
    kilogram = RangeModel.create_kilogram()
    ingredient = make_ingredient(nomenclature=make_nomenclature(1, kilogram), quantity=800)

    # Действие
    gross_weight = ingredient.gross_weight

    # Проверка
    assert gross_weight == pytest.approx(800)


def test_net_weight_loss_ratio_subtracted_from_gross():
    """Вес нетто равен весу брутто за вычетом потерь: 1000 г при потерях 35 % дают 650 г."""
    # Подготовка
    ingredient = make_ingredient(quantity=1000, loss_ratio=0.35)

    # Действие
    net_weight = ingredient.net_weight

    # Проверка
    assert net_weight == pytest.approx(650)


def test_net_weight_no_loss_equals_gross():
    """Без потерь вес нетто равен весу брутто."""
    # Подготовка
    ingredient = make_ingredient(nomenclature=make_nomenclature(0.92), quantity=40)

    # Действие и проверка
    assert ingredient.net_weight == pytest.approx(ingredient.gross_weight)


def test_weights_quantity_changed_recalculated():
    """После смены количества веса брутто и нетто пересчитываются."""
    # Подготовка
    ingredient = make_ingredient(quantity=100, loss_ratio=0.2)

    # Действие
    ingredient.quantity = 200

    # Проверка
    assert ingredient.gross_weight == pytest.approx(200)
    assert ingredient.net_weight == pytest.approx(160)


def test_weights_loss_ratio_changed_net_recalculated():
    """После смены доли потерь вес нетто пересчитывается, вес брутто не меняется."""
    # Подготовка
    ingredient = make_ingredient(quantity=100, loss_ratio=0.2)

    # Действие
    ingredient.loss_ratio = 0.5

    # Проверка
    assert ingredient.gross_weight == pytest.approx(100)
    assert ingredient.net_weight == pytest.approx(50)


def test_weights_nomenclature_unit_weight_changed_recalculated():
    """После смены веса базовой единицы у номенклатуры веса ингредиента пересчитываются."""
    # Подготовка
    nomenclature = make_nomenclature(1)
    ingredient = make_ingredient(nomenclature=nomenclature, quantity=100, loss_ratio=0.5)

    # Действие
    nomenclature.grams_per_base_unit = 2

    # Проверка
    assert ingredient.gross_weight == pytest.approx(200)
    assert ingredient.net_weight == pytest.approx(100)


def test_nomenclature_key_returns_nomenclature_id():
    """Ключ ингредиента в карте — идентификатор его номенклатуры."""
    # Подготовка
    nomenclature = make_nomenclature()
    ingredient = make_ingredient(nomenclature=nomenclature)

    # Действие
    result = ingredient.nomenclature_key()

    # Проверка
    assert result == nomenclature.id


def test_nomenclature_key_same_nomenclature_different_quantity_keys_equal():
    """Ингредиенты одной номенклатуры дают один ключ независимо от количества и потерь."""
    # Подготовка
    nomenclature = make_nomenclature()
    first = make_ingredient(nomenclature=nomenclature, quantity=10)
    second = make_ingredient(nomenclature=nomenclature, quantity=500, loss_ratio=0.5)

    # Действие и проверка
    assert first.nomenclature_key() == second.nomenclature_key()


def test_nomenclature_key_different_nomenclatures_keys_differ():
    """Ингредиенты разных номенклатур дают разные ключи, даже если наименования совпадают."""
    # Подготовка
    first = make_ingredient(nomenclature=make_nomenclature())
    second = make_ingredient(nomenclature=make_nomenclature())

    # Действие и проверка
    assert first.nomenclature_key() != second.nomenclature_key()


def test_init_ingredient_does_not_reference_recipe():
    """Ингредиент о технологических картах не знает: полуфабрикат собирает RecipeModel.as_ingredient."""
    # Действие
    ingredient = make_ingredient()

    # Проверка
    assert not hasattr(ingredient, "recipe")


def test_init_recipe_argument_passed_raises():
    """Конструктор не принимает карту: старая запись IngredientModel(..., recipe=...) больше не поддерживается."""
    # Подготовка
    nomenclature = make_nomenclature()

    # Действие и проверка
    with pytest.raises(TypeError):
        IngredientModel(nomenclature, 50, recipe=None)  # pyright: ignore[reportCallIssue]


def make_named(name: str, type: NomenclatureType = NomenclatureType.RAW_MATERIAL) -> NomenclatureModel:
    """Создаёт номенклатуру с заданными наименованием и типом, вес базовой единицы 1 г."""
    return NomenclatureModel(
        name, f"{name} (полное наименование)", NomenclatureGroupModel("Группа"), RangeModel("грамм", 1), type, 1
    )


def make_bouillon(quantity: float = 250, loss_ratio: float = 0) -> IngredientModel:
    """Создаёт составной ингредиент «Бульон»: кости 400 г с потерями 0,5 и соль 10 г без потерь."""
    return IngredientModel(
        make_named("Бульон", NomenclatureType.SEMI_FINISHED),
        quantity,
        loss_ratio,
        [IngredientModel(make_named("Кости"), 400, 0.5), IngredientModel(make_named("Соль"), 10)],
    )


def test_init_base_omitted_is_empty():
    """Без основания ингредиент — сырьё: основание пустое."""
    # Действие
    ingredient = make_ingredient()

    # Проверка
    assert ingredient.base == ()


def test_init_base_passed_copied_in_order():
    """Основание сохраняется в исходном порядке, но копиями: правка исходных объектов узел не меняет."""
    # Подготовка
    bones = IngredientModel(make_named("Кости"), 400)
    salt = IngredientModel(make_named("Соль"), 10)
    bouillon = IngredientModel(make_named("Бульон", NomenclatureType.SEMI_FINISHED), 250, base=[bones, salt])

    # Действие
    bones.quantity = 1000

    # Проверка
    assert [item.nomenclature for item in bouillon.base] == [bones.nomenclature, salt.nomenclature]
    assert all(item is not source for item, source in zip(bouillon.base, (bones, salt), strict=True))
    assert bouillon.gross_weight == pytest.approx(410)


def test_base_returned_items_changed_ingredient_unchanged():
    """Основание отдаётся копиями: правка полученного элемента не меняет вес узла."""
    # Подготовка
    bouillon = make_bouillon()

    # Действие
    bouillon.base[0].quantity = 1000

    # Проверка
    assert bouillon.gross_weight == pytest.approx(410)


def test_base_setter_not_allowed_raises():
    """Основание задаётся только в конструкторе."""
    # Подготовка
    bouillon = make_bouillon()

    # Действие и проверка
    with pytest.raises(AttributeError):
        bouillon.base = ()  # pyright: ignore[reportAttributeAccessIssue]


# Подготовка
@pytest.mark.parametrize("element", [None, "Кости", make_nomenclature()])
def test_init_base_not_ingredient_raises(element):
    """Элемент основания, не являющийся ингредиентом, вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        IngredientModel(make_named("Бульон", NomenclatureType.SEMI_FINISHED), 250, base=[element])


def test_init_base_duplicate_nomenclature_raises():
    """Номенклатура в основании уникальна, как и в составе карты."""
    # Подготовка
    bones = make_named("Кости")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        IngredientModel(
            make_named("Бульон", NomenclatureType.SEMI_FINISHED),
            250,
            base=[IngredientModel(bones, 100), IngredientModel(bones, 200)],
        )


def test_init_base_contains_own_nomenclature_raises():
    """Полуфабрикат не может состоять из самого себя, даже на втором уровне основания."""
    # Подготовка
    bouillon = make_named("Бульон", NomenclatureType.SEMI_FINISHED)
    inner = IngredientModel(make_named("Основа", NomenclatureType.SEMI_FINISHED), 100, base=[IngredientModel(bouillon, 50)])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        IngredientModel(bouillon, 250, base=[inner])


def test_gross_weight_composite_sum_of_base():
    """Брутто составного узла — сумма брутто основания; вес базовой единицы самого узла не учитывается."""
    # Подготовка
    bouillon = make_bouillon()

    # Действие
    gross_weight = bouillon.gross_weight

    # Проверка
    assert gross_weight == pytest.approx(410)


def test_net_weight_composite_sum_of_base_with_own_loss():
    """Нетто составного узла — сумма нетто основания за вычетом потерь узла: (200 + 10) * 0.9."""
    # Подготовка
    bouillon = make_bouillon(loss_ratio=0.1)

    # Действие
    net_weight = bouillon.net_weight

    # Проверка
    assert net_weight == pytest.approx(189)


def test_weights_two_level_base_calculated_recursively():
    """Основание само может быть составным: веса считаются рекурсивно на каждом уровне."""
    # Подготовка
    soup = IngredientModel(
        make_named("Суп", NomenclatureType.DISH),
        1,
        0.2,
        [make_bouillon(loss_ratio=0.1), IngredientModel(make_named("Картофель"), 100, 0.5)],
    )

    # Действие и проверка
    assert soup.gross_weight == pytest.approx(510)
    assert soup.net_weight == pytest.approx((189 + 50) * 0.8)


def test_quantity_setter_composite_scales_base():
    """Смена количества составного узла пропорционально масштабирует основание."""
    # Подготовка
    bouillon = make_bouillon(250)

    # Действие
    bouillon.quantity = 500

    # Проверка
    assert bouillon.quantity == 500
    assert [item.quantity for item in bouillon.base] == [pytest.approx(800), pytest.approx(20)]
    assert bouillon.gross_weight == pytest.approx(820)


def test_quantity_setter_invalid_value_composite_unchanged():
    """При ошибке проверки количество и основание составного узла не меняются."""
    # Подготовка
    bouillon = make_bouillon(250)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        bouillon.quantity = 0
    assert bouillon.quantity == 250
    assert bouillon.gross_weight == pytest.approx(410)


def test_loss_ratio_setter_composite_changes_net_only():
    """Потери составного узла влияют только на нетто, основание не меняется."""
    # Подготовка
    bouillon = make_bouillon()

    # Действие
    bouillon.loss_ratio = 0.5

    # Проверка
    assert bouillon.gross_weight == pytest.approx(410)
    assert bouillon.net_weight == pytest.approx(105)


def test_scaled_leaf_new_object_with_scaled_quantity():
    """Копия сырья получает умноженное количество, ту же номенклатуру и потери; исходник не меняется."""
    # Подготовка
    ingredient = make_ingredient(quantity=80, loss_ratio=0.25)

    # Действие
    copy = ingredient.scaled(0.5)

    # Проверка
    assert copy is not ingredient
    assert copy.nomenclature is ingredient.nomenclature
    assert copy.quantity == pytest.approx(40)
    assert copy.loss_ratio == 0.25
    assert ingredient.quantity == 80


def test_scaled_composite_base_scaled_recursively():
    """Основание составного узла масштабируется на всех уровнях."""
    # Подготовка
    soup = IngredientModel(make_named("Суп", NomenclatureType.DISH), 1, base=[make_bouillon(250)])

    # Действие
    copy = soup.scaled(2)

    # Проверка
    bouillon = copy.base[0]
    assert copy.quantity == 2
    assert bouillon.quantity == pytest.approx(500)
    assert [item.quantity for item in bouillon.base] == [pytest.approx(800), pytest.approx(20)]
    assert copy.gross_weight == pytest.approx(820)
    assert soup.gross_weight == pytest.approx(410)


def test_scaled_copy_changed_source_unchanged():
    """Копия независима: смена её количества не меняет исходный узел."""
    # Подготовка
    bouillon = make_bouillon()
    copy = bouillon.scaled(1)

    # Действие
    copy.quantity = 500

    # Проверка
    assert bouillon.quantity == 250
    assert bouillon.gross_weight == pytest.approx(410)


# Подготовка
@pytest.mark.parametrize("factor", [0, -1, float("nan"), float("inf"), True, None, "2"])
def test_scaled_invalid_factor_raises(factor):
    """Коэффициент масштабирования должен быть конечным числом больше нуля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_bouillon().scaled(factor)


def test_contains_same_nomenclature_returns_true():
    """Узел содержит собственную номенклатуру."""
    # Подготовка
    nomenclature = make_nomenclature()
    ingredient = make_ingredient(nomenclature=nomenclature)

    # Действие и проверка
    assert ingredient.contains(nomenclature) is True


def test_contains_other_nomenclature_returns_false():
    """Узел не содержит другую номенклатуру, даже если наименования совпадают."""
    # Подготовка
    ingredient = make_ingredient(nomenclature=make_nomenclature())

    # Действие и проверка
    assert ingredient.contains(make_nomenclature()) is False


def test_contains_nomenclature_deep_in_base_returns_true():
    """Номенклатура находится в основании на любой глубине."""
    # Подготовка
    bouillon = make_bouillon()
    bones = bouillon.base[0].nomenclature
    soup = IngredientModel(make_named("Суп", NomenclatureType.DISH), 1, base=[bouillon])

    # Действие и проверка
    assert soup.contains(bones) is True
    assert soup.contains(bouillon.nomenclature) is True
