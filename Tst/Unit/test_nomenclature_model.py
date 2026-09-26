import pytest
from Src.Core.base_entity import BaseEntity
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


def test_init_any_instance_is_base_entity():
    """Номенклатура является наследником BaseEntity."""
    # Действие
    result = isinstance(make_nomenclature(), BaseEntity)

    # Проверка
    assert result is True


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


@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_init_invalid_name_raises(name):
    """Пустое, состоящее из пробелов или не строковое наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(name=name)


@pytest.mark.parametrize("full_name", ["", "   ", None, 123])
def test_init_invalid_full_name_raises(full_name):
    """Пустое, состоящее из пробелов или не строковое полное наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(full_name=full_name)


@pytest.mark.parametrize("group", [None, "Сырьё", 1, RangeModel("грамм", 1)])
def test_init_invalid_group_raises(group):
    """Группа, не являющаяся NomenclatureGroupModel (в том числе другая модель), вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(group=group)


@pytest.mark.parametrize("range_", [None, "грамм", 1, NomenclatureGroupModel("Сырьё")])
def test_init_invalid_range_raises(range_):
    """Единица, не являющаяся RangeModel (в том числе другая модель), вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_nomenclature(range=range_)


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


def test_eq_same_data_different_ids_not_equal():
    """Две номенклатуры с одинаковыми данными, но разными идентификаторами не равны."""
    # Подготовка
    nomenclature1 = make_nomenclature()
    nomenclature2 = make_nomenclature()

    # Действие
    result = nomenclature1 == nomenclature2

    # Проверка
    assert result is False


def test_hash_name_changed_still_dict_key():
    """Хэш определяется идентификатором: после переименования номенклатура остаётся рабочим ключом словаря."""
    # Подготовка
    nomenclature = make_nomenclature()
    stock = {nomenclature: 10}

    # Действие
    nomenclature.name = "Другое наименование"

    # Проверка
    assert stock[nomenclature] == 10


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