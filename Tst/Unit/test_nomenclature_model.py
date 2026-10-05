import pytest
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel


def make_nomenclature(**overrides) -> NomenclatureModel:
    """Создаёт номенклатуру с корректными данными, подменяя переданные параметры."""
    params = {
        "name": "Мука",
        "full_name": "Мука пшеничная высшего сорта",
        "group": NomenclatureGroupModel("Сырьё"),
        "range": RangeModel("грамм", 1),
    }
    params.update(overrides)
    return NomenclatureModel(**params)


def test_init_valid_params_fields_set():
    """Номенклатура создаётся с переданными значениями всех полей и заданным идентификатором."""
    # Подготовка
    group = NomenclatureGroupModel("Сырьё")
    gram = RangeModel("грамм", 1)

    # Действие
    nomenclature = NomenclatureModel("Мука", "Мука пшеничная высшего сорта", group, gram)

    # Проверка
    assert nomenclature.name == "Мука"
    assert nomenclature.full_name == "Мука пшеничная высшего сорта"
    assert nomenclature.group is group
    assert nomenclature.range is gram
    assert nomenclature.id is not None


def test_init_derived_range_created():
    """Единицей измерения номенклатуры может быть производная единица (килограмм)."""
    # Подготовка
    kilogram = RangeModel("кг", 1000, RangeModel("грамм", 1))

    # Действие
    nomenclature = make_nomenclature(range=kilogram)

    # Проверка
    assert nomenclature.range is kilogram


def test_init_name_max_length_created():
    """Наименование ровно из 50 символов допустимо."""
    # Подготовка
    name = "a" * NomenclatureModel.NAME_MAX_LENGTH

    # Действие
    nomenclature = make_nomenclature(name=name)

    # Проверка
    assert nomenclature.name == name


def test_init_name_too_long_raises():
    """Наименование длиннее 50 символов вызывает ArgumentsException."""
    # Подготовка
    name = "a" * (NomenclatureModel.NAME_MAX_LENGTH + 1)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(name=name)


def test_init_name_spaces_not_counted_in_length():
    """Пробелы по краям наименования отбрасываются и не учитываются в длине."""
    # Подготовка
    name = "  " + "a" * NomenclatureModel.NAME_MAX_LENGTH + "  "

    # Действие
    nomenclature = make_nomenclature(name=name)

    # Проверка
    assert nomenclature.name == "a" * NomenclatureModel.NAME_MAX_LENGTH


def test_init_full_name_max_length_created():
    """Полное наименование ровно из 255 символов допустимо, лимит в 50 символов на него не действует."""
    # Подготовка
    full_name = "a" * NomenclatureModel.FULL_NAME_MAX_LENGTH

    # Действие
    nomenclature = make_nomenclature(full_name=full_name)

    # Проверка
    assert nomenclature.full_name == full_name


def test_init_full_name_too_long_raises():
    """Полное наименование длиннее 255 символов вызывает ArgumentsException."""
    # Подготовка
    full_name = "a" * (NomenclatureModel.FULL_NAME_MAX_LENGTH + 1)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(full_name=full_name)


def test_init_full_name_with_spaces_stripped():
    """Пробелы по краям полного наименования отбрасываются."""
    # Действие
    nomenclature = make_nomenclature(full_name="  Мука пшеничная  ")

    # Проверка
    assert nomenclature.full_name == "Мука пшеничная"


def test_init_group_and_range_swapped_raises():
    """Перепутанные местами группа и единица измерения вызывают ArgumentsException."""
    # Подготовка
    group = NomenclatureGroupModel("Сырьё")
    gram = RangeModel("грамм", 1)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NomenclatureModel("Мука", "Мука пшеничная", gram, group)  # pyright: ignore[reportArgumentType]


def test_setters_valid_values_updated():
    """Сеттеры обновляют наименование, полное наименование, группу и единицу измерения."""
    # Подготовка
    nomenclature = make_nomenclature()
    new_group = NomenclatureGroupModel("Полуфабрикаты")
    kilogram = RangeModel("кг", 1000, RangeModel("грамм", 1))

    # Действие
    nomenclature.name = "Тесто"
    nomenclature.full_name = "Тесто дрожжевое"
    nomenclature.group = new_group
    nomenclature.range = kilogram

    # Проверка
    assert nomenclature.name == "Тесто"
    assert nomenclature.full_name == "Тесто дрожжевое"
    assert nomenclature.group is new_group
    assert nomenclature.range is kilogram


# Подготовка
@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("name", "a" * 51),
        ("name", ""),
        ("full_name", "a" * 256),
        ("full_name", None),
        ("group", None),
        ("range", None),
    ],
)
def test_setters_invalid_value_raises_and_keeps_old(attribute, value):
    """Некорректное значение в сеттере вызывает ArgumentsException и не меняет прежнее значение."""
    # Подготовка
    nomenclature = make_nomenclature()
    old_value = getattr(nomenclature, attribute)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        setattr(nomenclature, attribute, value)
    assert getattr(nomenclature, attribute) == old_value


def test_init_flour_example_demonstration():
    """Демонстрация: две номенклатуры в одной группе с единицами грамм и килограмм."""
    # Подготовка
    raw = NomenclatureGroupModel("Сырьё")
    gram = RangeModel("грамм", 1)
    kilogram = RangeModel("кг", 1000, gram)

    # Действие
    flour = NomenclatureModel("Мука", "Мука пшеничная высшего сорта", raw, kilogram)
    salt = NomenclatureModel("Соль", "Соль поваренная пищевая", raw, gram)

    # Проверка
    assert flour.group is salt.group
    assert flour.range.base is salt.range
    assert flour.range.factor == 1000