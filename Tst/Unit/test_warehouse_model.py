import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Models.warehouse_model import WarehouseModel


def test_init_valid_name_created():
    """Склад создаётся с переданным наименованием и заданным идентификатором."""
    # Подготовка
    name = "Холодильник цеха"

    # Действие
    warehouse = WarehouseModel(name)

    # Проверка
    assert warehouse.name == name
    assert warehouse.id is not None


def test_init_any_instance_is_base_entity():
    """Склад является наследником BaseEntity."""
    # Подготовка
    warehouse = WarehouseModel("Основной")

    # Действие
    result = isinstance(warehouse, BaseEntity)

    # Проверка
    assert result is True


def test_init_name_with_spaces_stripped():
    """Пробелы по краям наименования отбрасываются."""
    # Подготовка
    name = "  Основной  "

    # Действие
    warehouse = WarehouseModel(name)

    # Проверка
    assert warehouse.name == "Основной"


def test_init_long_name_created():
    """Для склада ограничение в 50 символов не действует."""
    # Подготовка
    name = "a" * 100

    # Действие
    warehouse = WarehouseModel(name)

    # Проверка
    assert warehouse.name == name


def test_init_two_warehouses_different_ids():
    """Два склада с одинаковым наименованием получают разные идентификаторы и не равны."""
    # Подготовка
    warehouse1 = WarehouseModel("Основной")
    warehouse2 = WarehouseModel("Основной")

    # Действие
    result = warehouse1 == warehouse2

    # Проверка
    assert warehouse1.id != warehouse2.id
    assert result is False


@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_init_invalid_name_raises(name):
    """Пустое, состоящее из пробелов или не строковое наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        WarehouseModel(name)