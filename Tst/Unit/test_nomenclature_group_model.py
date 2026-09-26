import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_group_model import NomenclatureGroupModel


def test_init_valid_name_created():
    """Группа номенклатуры создаётся с переданным наименованием и заданным идентификатором."""
    # Подготовка
    name = "Сырьё"

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name
    assert group.id is not None


def test_init_any_instance_is_base_entity():
    """Группа номенклатуры является наследником BaseEntity."""
    # Подготовка
    group = NomenclatureGroupModel("Сырьё")

    # Действие
    result = isinstance(group, BaseEntity)

    # Проверка
    assert result is True


def test_init_name_with_spaces_stripped():
    """Пробелы по краям наименования отбрасываются."""
    # Подготовка
    name = "  Сырьё  "

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == "Сырьё"


def test_init_long_name_created():
    """Для группы номенклатуры ограничение в 50 символов не действует."""
    # Подготовка
    name = "a" * 100

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name


def test_init_two_groups_different_ids():
    """Две группы с одинаковым наименованием получают разные идентификаторы и не равны."""
    # Подготовка
    group1 = NomenclatureGroupModel("Сырьё")
    group2 = NomenclatureGroupModel("Сырьё")

    # Действие
    result = group1 == group2

    # Проверка
    assert group1.id != group2.id
    assert result is False


@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_init_invalid_name_raises(name):
    """Пустое, состоящее из пробелов или не строковое наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NomenclatureGroupModel(name)