import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel


def make_nomenclature(grams_per_base_unit: float = 1, range: RangeModel | None = None) -> NomenclatureModel:
    """Создаёт номенклатуру с корректными данными и заданным весом базовой единицы."""
    return NomenclatureModel(
        "Картофель",
        "Картофель свежий",
        NomenclatureGroupModel("Овощи"),
        range if range is not None else RangeModel("грамм", 1),
        NomenclatureType.RAW_MATERIAL,
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
    kilogram = RangeModel.create_kilogramm()
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
