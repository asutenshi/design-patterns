import uuid

import pytest
from Src.Core.abstract_report import AbstractReport
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel

# Защищённые помощники проверяются напрямую: на них опираются все форматы отчётов
_format_scalar = AbstractReport._format_scalar  # pyright: ignore[reportPrivateUsage]
_is_scalar = AbstractReport._is_scalar  # pyright: ignore[reportPrivateUsage]
_is_reference = AbstractReport._is_reference  # pyright: ignore[reportPrivateUsage]


def test_init_abstract_report_raises_type_error():
    """Абстрактный отчёт создать нельзя: build() не реализован."""
    # Действие и проверка
    with pytest.raises(TypeError):
        _ = AbstractReport()  # pyright: ignore[reportAbstractUsage]


# Подготовка
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("текст", "текст"),
        (5, "5"),
        (True, "True"),
        (400.0, "400"),
        (0.05, "0.05"),
        (380.00000000000006, "380"),
        (2.0004, "2"),
        (2.0006, "2.001"),
        (-0.0001, "0"),
        (NomenclatureType.DISH, "блюдо"),
    ],
)
def test_format_scalar_value_returns_expected_text(value: object, expected: str):
    """Простые значения приводятся к строке: перечисление — значением, дробь — с округлением до 3 знаков."""
    # Действие
    text = _format_scalar(value)

    # Проверка
    assert text == expected


def test_format_scalar_uuid_returns_canonical_text():
    """Код выводится в каноническом виде UUID."""
    # Подготовка
    code = uuid.uuid4()

    # Действие и проверка
    assert _format_scalar(code) == str(code)


# Подготовка
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("строка", True),
        (1, True),
        (1.5, True),
        (NomenclatureType.DISH, True),
        (uuid.uuid4(), True),
        ([], False),
        ((), False),
        (object(), False),
    ],
)
def test_is_scalar_value_returns_expected(value: object, expected: bool):
    """Простыми считаются None, строки, числа, перечисления и UUID; списки и объекты — нет."""
    # Действие и проверка
    assert _is_scalar(value) is expected


def test_is_reference_named_entity_returns_true_and_ingredient_false():
    """Сущность с наименованием выводится ссылкой, ингредиент (часть «Компоновщика») раскрывается."""
    # Подготовка
    kilogram = RangeModel.create_kilogram()
    nomenclature = NomenclatureModel.create_raw_material(
        "Свёкла", "Свёкла столовая", NomenclatureGroupModel.create_vegetables(), kilogram, 1
    )
    ingredient = IngredientModel(nomenclature, 100)

    # Действие и проверка
    assert _is_reference(kilogram) is True
    assert _is_reference(nomenclature) is True
    assert _is_reference(ingredient) is False
