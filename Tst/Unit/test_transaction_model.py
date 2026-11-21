from datetime import datetime

import pytest
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.transaction_model import TransactionModel
from Src.Models.warehouse_model import WarehouseModel

# Дата операции для тестов
PERIOD = datetime(2026, 10, 5, 11, 0)


@pytest.fixture
def kilogram() -> RangeModel:
    """Килограмм с базовой единицей «грамм»."""
    return RangeModel.create_kilogram()


@pytest.fixture
def beef(kilogram: RangeModel) -> NomenclatureModel:
    """Говядина, которая учитывается в килограммах."""
    return NomenclatureModel.create_raw_material(
        "Говядина", "Говядина охлаждённая", NomenclatureGroupModel.create_meat(), kilogram, 1
    )


@pytest.fixture
def warehouse() -> WarehouseModel:
    """Склад ресторана."""
    return WarehouseModel.create_restaurant_warehouse()


def test_init_valid_values_sets_fields(beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel):
    """Запись журнала хранит номенклатуру, склад, единицу, количество со знаком и дату как переданы."""
    # Действие
    transaction = TransactionModel(beef, warehouse, kilogram, -2.5, PERIOD)

    # Проверка
    assert transaction.nomenclature is beef
    assert transaction.warehouse is warehouse
    assert transaction.range is kilogram
    assert transaction.quantity == -2.5
    assert transaction.period == PERIOD


def test_init_base_unit_of_nomenclature_range_is_accepted(
    beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel
):
    """Говядину в килограммах можно провести в граммах: у обеих единиц одна база."""
    # Действие
    transaction = TransactionModel(beef, warehouse, kilogram.base, -500, PERIOD)

    # Проверка
    assert transaction.range is kilogram.base


def test_init_range_with_other_base_raises(beef: NomenclatureModel, warehouse: WarehouseModel):
    """Литр приводится к миллилитру, а говядина к грамму: такую запись провести нельзя."""
    # Подготовка
    liter = RangeModel.create_liter()

    # Действие и проверка
    with pytest.raises(ArgumentsException, match="Говядина"):
        _ = TransactionModel(beef, warehouse, liter, 1, PERIOD)


def test_init_separately_created_gram_raises(beef: NomenclatureModel, warehouse: WarehouseModel):
    """Другой объект «грамм» — другая база, хотя наименование совпадает: базы сравниваются по тождеству."""
    # Подготовка
    other_kilogram = RangeModel.create_kilogram()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TransactionModel(beef, warehouse, other_kilogram, 1, PERIOD)


def test_init_zero_quantity_raises(beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel):
    """Нулевое количество не означает ни прихода, ни расхода и отклоняется."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TransactionModel(beef, warehouse, kilogram, 0, PERIOD)


def test_init_period_not_datetime_raises(beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel):
    """Дата операции передаётся объектом datetime, строка в конструкторе не принимается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TransactionModel(beef, warehouse, kilogram, 1, "2026-10-05")  # pyright: ignore[reportArgumentType]


def test_from_dict_iso_period_creates_transaction(
    beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel
):
    """Фабричный метод превращает дату из строки ISO 8601 в datetime."""
    # Подготовка
    data: dict[str, object] = {
        "nomenclature": beef,
        "warehouse": warehouse,
        "range": kilogram,
        "quantity": 3,
        "period": "2026-10-05T11:00:00",
    }

    # Действие
    transaction = TransactionModel.from_dict(data)

    # Проверка
    assert transaction.period == PERIOD
    assert transaction.quantity == 3


def test_references_returns_nomenclature_warehouse_and_range(
    beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel
):
    """Запись ссылается на номенклатуру, склад и единицу: их нельзя удалить, пока запись в журнале."""
    # Подготовка
    transaction = TransactionModel(beef, warehouse, kilogram, 1, PERIOD)

    # Действие
    references = transaction.references()

    # Проверка
    assert references == [beef, warehouse, kilogram]
