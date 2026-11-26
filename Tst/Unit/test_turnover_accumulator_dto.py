from datetime import date, datetime

import pytest
from Src.Core.exception import ArgumentsException, OperationException
from Src.Dtos.turnover_accumulator_dto import TurnoverAccumulatorDto
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.transaction_model import TransactionModel
from Src.Models.warehouse_model import WarehouseModel


@pytest.fixture
def gram() -> RangeModel:
    """Базовая единица «грамм»."""
    return RangeModel.create_kilogram().base


@pytest.fixture
def kilogram(gram: RangeModel) -> RangeModel:
    """Килограмм с базовой единицей «грамм»."""
    return RangeModel("килограмм", 1000, gram)


@pytest.fixture
def beef(kilogram: RangeModel) -> NomenclatureModel:
    """Номенклатура «Говядина»."""
    return NomenclatureModel.create_raw_material(
        "Говядина", "Говядина охлаждённая", NomenclatureGroupModel.create_meat(), kilogram, 1
    )


@pytest.fixture
def warehouse() -> WarehouseModel:
    """Склад ресторана."""
    return WarehouseModel.create_restaurant_warehouse()


def test_accumulator_default_values(beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel):
    """По умолчанию начальные колонки аккумулятора равны 0.0."""
    # Действие
    acc = TurnoverAccumulatorDto(beef, warehouse, gram)

    # Проверка
    assert acc.nomenclature is beef
    assert acc.warehouse is warehouse
    assert acc.range is gram
    assert acc.opening == 0.0
    assert acc.income == 0.0
    assert acc.outcome == 0.0


def test_accumulator_non_base_range_raises(beef: NomenclatureModel, warehouse: WarehouseModel, kilogram: RangeModel):
    """Попытка создать аккумулятор с небазовой единицей измерения — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        TurnoverAccumulatorDto(beef, warehouse, kilogram)


def test_accumulator_record_before_start_adds_to_opening(
    beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel, kilogram: RangeModel
):
    """Проводка до начала периода увеличивает остаток на начало с учётом коэффициента единицы."""
    # Подготовка
    acc = TurnoverAccumulatorDto(beef, warehouse, gram)
    tx = TransactionModel(beef, warehouse, kilogram, 3.0, datetime(2026, 9, 15, 10, 0))

    # Действие
    acc.record(tx, date(2026, 10, 1))

    # Проверка (3 кг = 3000 г)
    assert acc.opening == 3000.0
    assert acc.income == 0.0
    assert acc.outcome == 0.0


def test_accumulator_record_in_period_positive_adds_to_income(
    beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel, kilogram: RangeModel
):
    """Положительная проводка в периоде увеличивает приход."""
    # Подготовка
    acc = TurnoverAccumulatorDto(beef, warehouse, gram)
    tx = TransactionModel(beef, warehouse, kilogram, 2.5, datetime(2026, 10, 15, 12, 0))

    # Действие
    acc.record(tx, date(2026, 10, 1))

    # Проверка (2.5 кг = 2500 г)
    assert acc.opening == 0.0
    assert acc.income == 2500.0
    assert acc.outcome == 0.0


def test_accumulator_record_in_period_negative_adds_to_outcome(
    beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel, kilogram: RangeModel
):
    """Отрицательная проводка в периоде увеличивает расход положительным числом."""
    # Подготовка
    acc = TurnoverAccumulatorDto(beef, warehouse, gram)
    tx = TransactionModel(beef, warehouse, kilogram, -1.5, datetime(2026, 10, 20, 14, 0))

    # Действие
    acc.record(tx, date(2026, 10, 1))

    # Проверка (1.5 кг = 1500 г)
    assert acc.opening == 0.0
    assert acc.income == 0.0
    assert acc.outcome == 1500.0


def test_accumulator_record_different_base_range_raises(
    beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel, kilogram: RangeModel
):
    """Проводка с базовой единицей, не совпадающей с базой строки (например, сменили единицу номенклатуры), — OperationException."""
    # Подготовка
    tx = TransactionModel(beef, warehouse, kilogram, 5.0, datetime(2026, 10, 5, 10, 0))
    # Меняем единицу номенклатуры на литр после создания проводки
    liter = RangeModel.create_liter()
    beef.range = liter

    # Создаём аккумулятор с новой базовой единицей литра
    acc_liter = TurnoverAccumulatorDto(beef, warehouse, liter.base)

    # Действие и проверка: проводка в килограммах не подходит аккумулятору с базой миллилитр
    with pytest.raises(OperationException):
        acc_liter.record(tx, date(2026, 10, 1))


def test_accumulator_to_row_creates_turnover_row(
    beef: NomenclatureModel, warehouse: WarehouseModel, gram: RangeModel
):
    """Метод to_row создаёт TurnoverRow с вычисленным остатком на конец."""
    # Подготовка
    acc = TurnoverAccumulatorDto(beef, warehouse, gram, opening=1000.0, income=500.0, outcome=300.0)

    # Действие
    row = acc.to_row()

    # Проверка
    assert row.nomenclature is beef
    assert row.warehouse is warehouse
    assert row.range is gram
    assert row.opening == 1000.0
    assert row.income == 500.0
    assert row.outcome == 300.0
    assert row.closing == 1200.0
