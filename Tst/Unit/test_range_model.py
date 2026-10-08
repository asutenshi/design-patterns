import pytest
from Src.Core.exception import ArgumentsException
from Src.Models.range_model import RangeModel


def test_init_base_unit_base_is_itself():
    """Единица без указанной базы является базовой: ссылается на себя, коэффициент равен 1."""
    # Подготовка
    name = "грамм"

    # Действие
    gram = RangeModel(name, 1)

    # Проверка
    assert gram.name == name
    assert gram.factor == 1
    assert gram.base is gram
    assert gram.is_base is True


def test_init_base_unit_float_one_created():
    """Коэффициент базовой единицы 1.0 допустим, так как равен 1."""
    # Действие
    gram = RangeModel("грамм", 1.0)

    # Проверка
    assert gram.is_base is True


def test_init_derived_unit_base_and_factor_set():
    """Производная единица хранит переданную базовую единицу и коэффициент."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие
    kilogram = RangeModel("кг", 1000, gram)

    # Проверка
    assert kilogram.name == "кг"
    assert kilogram.factor == 1000
    assert kilogram.base is gram
    assert kilogram.is_base is False


def test_init_derived_unit_fractional_factor_created():
    """Производная единица может иметь дробный коэффициент (миллиграмм = 0.001 грамма)."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие
    milligram = RangeModel("мг", 0.001, gram)

    # Проверка
    assert milligram.factor == 0.001
    assert milligram.base is gram


def test_init_derived_unit_factor_one_created():
    """Производная единица может иметь коэффициент 1 (синоним базовой единицы)."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие
    gr = RangeModel("гр", 1, gram)

    # Проверка
    assert gr.base is gram
    assert gr.is_base is False


def test_init_several_derived_units_share_base():
    """Несколько производных единиц могут ссылаться на одну базовую."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие
    kilogram = RangeModel("кг", 1000, gram)
    tonne = RangeModel("т", 1_000_000, gram)

    # Проверка
    assert kilogram.base is gram
    assert tonne.base is gram


# Подготовка
@pytest.mark.parametrize("factor", [2, 0.5, 1000])
def test_init_base_unit_factor_not_one_raises(factor):
    """У базовой единицы коэффициент, отличный от 1, вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        RangeModel("грамм", factor)


def test_init_derived_unit_zero_factor_raises():
    """Нулевой коэффициент производной единицы вызывает ArgumentsException.

    Остальные случаи (отрицательный, NaN, бесконечность, bool, не число) проверены
    в test_common_validator.
    """
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        RangeModel("кг", 0, gram)


def test_init_base_not_range_model_raises():
    """База, заданная не единицей измерения (например, строкой), вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        RangeModel("кг", 1000, "грамм")  # pyright: ignore[reportArgumentType]


def test_init_base_is_derived_unit_raises():
    """Производная единица в качестве базовой вызывает ArgumentsException."""
    # Подготовка
    gram = RangeModel("грамм", 1)
    kilogram = RangeModel("кг", 1000, gram)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        RangeModel("т", 1000, kilogram)


# Подготовка
@pytest.mark.parametrize("attribute", ["base", "factor", "is_base"])
def test_readonly_properties_assignment_raises(attribute):
    """Свойства base, factor и is_base только для чтения: присваивание вызывает AttributeError."""
    # Подготовка
    gram = RangeModel("грамм", 1)
    kilogram = RangeModel("кг", 1000, gram)

    # Действие и проверка
    with pytest.raises(AttributeError):
        setattr(kilogram, attribute, gram)


def test_create_kilogram_returns_kilogram_with_gram_base():
    """Фабрика килограмма возвращает килограмм с коэффициентом 1000 и базовым граммом."""
    # Действие
    kilogram = RangeModel.create_kilogram()

    # Проверка
    assert kilogram.name == "килограмм"
    assert kilogram.factor == 1000
    assert kilogram.is_base is False
    assert kilogram.base.name == "грамм"
    assert kilogram.base.factor == 1
    assert kilogram.base.is_base is True


def test_create_liter_returns_liter_with_milliliter_base():
    """Фабрика литра возвращает литр с коэффициентом 1000 и базовым миллилитром."""
    # Действие
    liter = RangeModel.create_liter()

    # Проверка
    assert liter.name == "литр"
    assert liter.factor == 1000
    assert liter.is_base is False
    assert liter.base.name == "миллилитр"
    assert liter.base.factor == 1
    assert liter.base.is_base is True


def test_create_piece_returns_base_unit():
    """Фабрика штуки возвращает базовую единицу с коэффициентом 1."""
    # Действие
    piece = RangeModel.create_piece()

    # Проверка
    assert piece.name == "штука"
    assert piece.factor == 1
    assert piece.is_base is True


# Подготовка
@pytest.mark.parametrize(
    "factory", [RangeModel.create_kilogram, RangeModel.create_liter, RangeModel.create_piece], ids=lambda f: f.__name__
)
def test_create_each_call_returns_new_instance(factory):
    """Каждый вызов фабрики создаёт новый объект, а не возвращает общий экземпляр."""
    # Действие
    first = factory()
    second = factory()

    # Проверка
    assert first is not second
    assert first != second
    assert first.base is not second.base


def test_init_gram_and_kilogram_example_demonstration():
    """Демонстрация работы с единицей измерения на примере из ТЗ: грамм и килограмм."""
    # Подготовка
    base_range = RangeModel("грамм", 1)

    # Действие
    new_range = RangeModel("кг", 1000, base_range)

    # Проверка
    assert base_range.base is base_range
    assert base_range.factor == 1
    assert new_range.base is base_range
    assert new_range.factor == 1000
    assert new_range.factor * 2 == 2000  # 2 кг = 2000 грамм
    assert base_range != new_range