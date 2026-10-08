import pytest
from Src.Core.named_entity import NamedEntity
from Src.Models.warehouse_model import WarehouseModel

# Проверки наименования и идентификатора (пробелы, пустые и не строковые значения,
# уникальность id) написаны один раз для NamedEntity и BaseEntity: см. test_named_entity,
# test_entities и test_inheritance_contracts.


def test_init_valid_name_created():
    """Склад создаётся с переданным наименованием и заданным идентификатором."""
    # Подготовка
    name = "Холодильник цеха"

    # Действие
    warehouse = WarehouseModel(name)

    # Проверка
    assert warehouse.name == name
    assert warehouse.id is not None


def test_init_any_instance_is_named_entity():
    """Склад является наследником NamedEntity и получает от него наименование."""
    # Подготовка
    warehouse = WarehouseModel("Основной")

    # Действие
    result = isinstance(warehouse, NamedEntity)

    # Проверка
    assert result is True


def test_init_long_name_created():
    """Для склада ограничение в 50 символов не действует."""
    # Подготовка
    name = "a" * 100

    # Действие
    warehouse = WarehouseModel(name)

    # Проверка
    assert warehouse.name == name


# Подготовка
@pytest.mark.parametrize(
    ("factory", "expected_name"),
    [
        (WarehouseModel.create_restaurant_warehouse, "Склад ресторана"),
        (WarehouseModel.create_workshop_warehouse, "Склад производственного цеха"),
    ],
    ids=lambda value: value.__name__ if callable(value) else value,
)
def test_create_warehouse_returns_warehouse_with_expected_name(factory, expected_name):
    """Фабрика создаёт склад с ожидаемым наименованием, каждый вызов — новый объект."""
    # Действие
    first = factory()
    second = factory()

    # Проверка
    assert isinstance(first, WarehouseModel)
    assert first.name == expected_name
    assert first is not second
