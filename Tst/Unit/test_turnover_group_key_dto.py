import pytest
from Src.Core.exception import ArgumentsException
from Src.Dtos.turnover_group_key_dto import TurnoverGroupKeyDto
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


@pytest.fixture
def beef() -> NomenclatureModel:
    """Номенклатура «Говядина»."""
    group = NomenclatureGroupModel.create_meat()
    kilogram = RangeModel.create_kilogram()
    return NomenclatureModel.create_raw_material("Говядина", "Говядина охлаждённая", group, kilogram, 1)


@pytest.fixture
def restaurant_warehouse() -> WarehouseModel:
    """Склад ресторана."""
    return WarehouseModel.create_restaurant_warehouse()


def test_turnover_group_key_properties(beef: NomenclatureModel, restaurant_warehouse: WarehouseModel):
    """Свойства возвращают переданные номенклатуру и склад."""
    # Действие
    key = TurnoverGroupKeyDto(beef, restaurant_warehouse)

    # Проверка
    assert key.nomenclature is beef
    assert key.warehouse is restaurant_warehouse


# Подготовка
@pytest.mark.parametrize(
    ("nomenclature", "warehouse"),
    [
        (None, WarehouseModel.create_restaurant_warehouse()),
        ("Говядина", WarehouseModel.create_restaurant_warehouse()),
        (
            NomenclatureModel.create_raw_material(
                "Говядина",
                "Говядина охлаждённая",
                NomenclatureGroupModel.create_meat(),
                RangeModel.create_kilogram(),
                1,
            ),
            None,
        ),
        (
            NomenclatureModel.create_raw_material(
                "Говядина",
                "Говядина охлаждённая",
                NomenclatureGroupModel.create_meat(),
                RangeModel.create_kilogram(),
                1,
            ),
            "Склад",
        ),
    ],
    ids=["none_nomenclature", "str_nomenclature", "none_warehouse", "str_warehouse"],
)
def test_turnover_group_key_invalid_arguments_raises(nomenclature: object, warehouse: object):
    """Неверный тип номенклатуры или склада — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        TurnoverGroupKeyDto(nomenclature, warehouse)  # pyright: ignore[reportArgumentType]


def test_turnover_group_key_equality_and_hash(beef: NomenclatureModel, restaurant_warehouse: WarehouseModel):
    """Ключи с одинаковыми кодами сущностей равны и имеют одинаковый хэш."""
    # Подготовка
    key1 = TurnoverGroupKeyDto(beef, restaurant_warehouse)
    key2 = TurnoverGroupKeyDto(beef, restaurant_warehouse)
    workshop = WarehouseModel.create_workshop_warehouse()
    key_other = TurnoverGroupKeyDto(beef, workshop)

    # Проверка
    assert key1 == key2
    assert hash(key1) == hash(key2)
    assert key1 != key_other
    assert key1 != "не ключ"
    assert key1 is not None

    # Использование в качестве ключа словаря
    mapping = {key1: "строка 1"}
    assert mapping[key2] == "строка 1"
