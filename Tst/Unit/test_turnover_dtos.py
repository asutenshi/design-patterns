from datetime import date

import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.filter_type import FilterType
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.turnover_report import TurnoverReport
from Src.Dtos.turnover_request_dto import TurnoverRequestDto
from Src.Dtos.turnover_row import TurnoverRow
from Src.Logics.converter_factory import ConverterFactory
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


@pytest.fixture
def kilogram() -> RangeModel:
    """Килограмм с базовой единицей «грамм»."""
    return RangeModel.create_kilogram()


@pytest.fixture
def beef_row(kilogram: RangeModel) -> TurnoverRow:
    """Строка ОСВ по говядине на складе ресторана за октябрь."""
    beef = NomenclatureModel.create_raw_material(
        "Говядина", "Говядина охлаждённая", NomenclatureGroupModel.create_meat(), kilogram, 1
    )
    return TurnoverRow(beef, WarehouseModel.create_restaurant_warehouse(), kilogram.base, 3000, 3000, 4000)


def test_request_from_dict_full_body_creates_request():
    """Тело с обеими датами и условием превращается в запрос с датами и FilterDto."""
    # Подготовка
    data: dict[str, object] = {
        "start": "2026-10-01",
        "end": "2026-10-31",
        "filters": [{"field_name": "nomenclature.name", "filter_type": "EQUALS", "value": "Говядина"}],
    }

    # Действие
    request = TurnoverRequestDto.from_dict(data)

    # Проверка
    assert request.start == date(2026, 10, 1)
    assert request.end == date(2026, 10, 31)
    assert [(item.field_name, item.filter_type, item.value) for item in request.filter.filters] == [
        ("nomenclature.name", FilterType.EQUALS, "Говядина")
    ]


def test_request_from_dict_without_dates_leaves_them_empty():
    """Даты необязательны: без них границы остаются None, их подставит сервис."""
    # Действие
    request = TurnoverRequestDto.from_dict({"filters": []})

    # Проверка
    assert request.start is None
    assert request.end is None
    assert request.filter.filters == []


def test_request_from_dict_without_filters_raises():
    """Поле filters обязательно, как и в обычном фильтре: пустой список пишется явно."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TurnoverRequestDto.from_dict({"start": "2026-10-01"})


# Подготовка
@pytest.mark.parametrize("value", ["01.10.2026", "2026-10-01T10:00:00", 20261001])
def test_request_from_dict_invalid_date_raises(value: object):
    """Дата принимается только строкой ГГГГ-ММ-ДД: другой формат и время отклоняются."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TurnoverRequestDto.from_dict({"start": value, "filters": []})


def test_request_start_after_end_raises():
    """Начало периода позже конца — ошибка запроса."""
    # Действие и проверка
    with pytest.raises(ArgumentsException, match="позже"):
        _ = TurnoverRequestDto(date(2026, 11, 1), date(2026, 10, 31), FilterDto([]))


def test_request_same_start_and_end_is_valid():
    """Период из одного дня допустим: обе границы включительные."""
    # Действие
    request = TurnoverRequestDto(date(2026, 10, 5), date(2026, 10, 5), FilterDto([]))

    # Проверка
    assert request.start == request.end


def test_row_closing_is_opening_plus_income_minus_outcome(beef_row: TurnoverRow):
    """Остаток на конец вычисляется из остальных колонок: 3000 + 3000 − 4000."""
    # Действие
    closing = beef_row.closing

    # Проверка
    assert closing == 2000


def test_row_negative_outcome_raises(beef_row: TurnoverRow):
    """Расход пишется положительным числом: знак уже учтён названием колонки."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TurnoverRow(beef_row.nomenclature, beef_row.warehouse, beef_row.range, 0, 0, -1)


def test_row_negative_opening_is_allowed(beef_row: TurnoverRow):
    """Остаток на начало может быть отрицательным: списание «под сальдо» (п. 2.4 ТЗ)."""
    # Действие
    row = TurnoverRow(beef_row.nomenclature, beef_row.warehouse, beef_row.range, -500, 0, 0)

    # Проверка
    assert row.closing == -500


def test_row_not_base_range_raises(beef_row: TurnoverRow, kilogram: RangeModel):
    """Количества строки записаны в базовой единице, килограмм не принимается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException, match="базовая"):
        _ = TurnoverRow(beef_row.nomenclature, beef_row.warehouse, kilogram, 0, 0, 0)


def test_report_start_after_end_raises():
    """Отчёт с перевёрнутым периодом не создаётся."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TurnoverReport(date(2026, 11, 1), date(2026, 10, 1), [])


def test_report_converter_writes_period_and_rows_with_closing(beef_row: TurnoverRow):
    """ConverterFactory записывает период строками ISO 8601, а в строке есть вычисленный остаток на конец."""
    # Подготовка
    report = TurnoverReport(date(2026, 10, 1), date(2026, 10, 31), [beef_row])

    # Действие
    data = ConverterFactory().convert(report)

    # Проверка
    assert isinstance(data, dict)
    assert data["start"] == "2026-10-01"
    assert data["end"] == "2026-10-31"
    rows = data["rows"]
    assert isinstance(rows, list)
    row = rows[0]
    assert isinstance(row, dict)
    assert (row["opening"], row["income"], row["outcome"], row["closing"]) == (3000, 3000, 4000, 2000)
