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
