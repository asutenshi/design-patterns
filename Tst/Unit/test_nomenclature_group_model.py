import pytest
from Src.Core.named_entity import NamedEntity
from Src.Models.nomenclature_group_model import NomenclatureGroupModel

# Проверки наименования и идентификатора (пробелы, пустые и не строковые значения,
# уникальность id) написаны один раз для NamedEntity и BaseEntity: см. test_named_entity,
# test_entities и test_inheritance_contracts.


def test_init_valid_name_created():
    """Группа номенклатуры создаётся с переданным наименованием и заданным идентификатором."""
    # Подготовка
    name = "Сырьё"

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name
    assert group.id is not None


def test_init_any_instance_is_named_entity():
    """Группа номенклатуры является наследником NamedEntity и получает от него наименование."""
    # Подготовка
    group = NomenclatureGroupModel("Сырьё")

    # Действие
    result = isinstance(group, NamedEntity)

    # Проверка
    assert result is True


def test_init_long_name_created():
    """Для группы ограничение в 50 символов не действует."""
    # Подготовка
    name = "a" * 100

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name


# Подготовка
@pytest.mark.parametrize(
    ("factory", "expected_name"),
    [
        (NomenclatureGroupModel.create_meat, "Мясные продукты"),
        (NomenclatureGroupModel.create_dairy, "Молочные продукты"),
        (NomenclatureGroupModel.create_vegetables, "Овощи"),
        (NomenclatureGroupModel.create_grocery, "Бакалея"),
        (NomenclatureGroupModel.create_semi_finished, "Полуфабрикаты"),
        (NomenclatureGroupModel.create_packaging, "Упаковка"),
    ],
    ids=lambda value: value.__name__ if callable(value) else value,
)
def test_create_group_returns_group_with_expected_name(factory, expected_name):
    """Фабрика создаёт группу с ожидаемым наименованием, каждый вызов — новый объект."""
    # Действие
    first = factory()
    second = factory()

    # Проверка
    assert isinstance(first, NomenclatureGroupModel)
    assert first.name == expected_name
    assert first is not second
