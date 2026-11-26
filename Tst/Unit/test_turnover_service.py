from datetime import date

import pytest
from Src.Core.exception import OperationException
from Src.Core.filter_type import FilterType
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.filter_item_dto import FilterItemDto
from Src.Dtos.turnover_report import TurnoverReport
from Src.Dtos.turnover_request_dto import TurnoverRequestDto
from Src.Logics.storage_manager import StorageManager
from Src.Logics.turnover_service import TurnoverService

# Журнал начальных данных (StorageManager._create_transactions), количества в базовых единицах:
#   01.09 Говядина, Склад ресторана            +5000 г
#   10.09 Говядина, Склад ресторана            −2000 г
#   03.10 Молоко, Склад производственного цеха +5000 мл
#   05.10 Говядина, Склад ресторана            +3000 г
#   07.10 Картофель, Склад ресторана          +10000 г
#   12.10 Говядина, Склад ресторана            −4000 г
#   20.10 Молоко, Склад производственного цеха −1500 мл
#   31.10 23:00 Говядина, Склад цеха           +2000 г
#   15.11 Говядина, Склад ресторана            +1000 г

# Строка ОСВ в удобном для сравнения виде
type Row = tuple[str, str, str, float, float, float, float]

RESTAURANT = "Склад ресторана"
WORKSHOP = "Склад производственного цеха"


def build(storage: StorageManager, start: date | None, end: date | None, *filters: FilterItemDto) -> TurnoverReport:
    """Строит ОСВ по хранилищу с указанным периодом и условиями."""
    return TurnoverService(storage).build(TurnoverRequestDto(start, end, FilterDto(list(filters))))


def rows(report: TurnoverReport) -> list[Row]:
    """Описывает строки отчёта: номенклатура, склад, единица и четыре колонки."""
    return [
        (
            row.nomenclature.name,
            row.warehouse.name,
            row.range.name,
            row.opening,
            row.income,
            row.outcome,
            row.closing,
        )
        for row in report.rows
    ]


def test_build_october_groups_by_nomenclature_and_warehouse(first_start_storage: StorageManager):
    """ОСВ за октябрь: строка на каждую пару «номенклатура + склад» в порядке первой записи, всё в базовых единицах."""
    # Действие
    report = build(first_start_storage, date(2026, 10, 1), date(2026, 10, 31))

    # Проверка
    assert rows(report) == [
        ("Говядина", RESTAURANT, "грамм", 3000, 3000, 4000, 2000),
        ("Молоко", WORKSHOP, "миллилитр", 0, 5000, 1500, 3500),
        ("Картофель", RESTAURANT, "грамм", 0, 10000, 0, 10000),
        ("Говядина", WORKSHOP, "грамм", 0, 2000, 0, 2000),
    ]


def test_build_keeps_requested_period(first_start_storage: StorageManager):
    """В отчёт попадает период из запроса."""
    # Действие
    report = build(first_start_storage, date(2026, 10, 1), date(2026, 10, 31))

    # Проверка
    assert (report.start, report.end) == (date(2026, 10, 1), date(2026, 10, 31))


def test_build_start_day_records_go_to_turnover(first_start_storage: StorageManager):
    """Начало включительно: запись от 05.10 — приход, а записи до 05.10 — остаток на начало."""
    # Действие
    report = build(first_start_storage, date(2026, 10, 5), date(2026, 10, 31))

    # Проверка
    assert rows(report)[:2] == [
        ("Говядина", RESTAURANT, "грамм", 3000, 3000, 4000, 2000),
        ("Молоко", WORKSHOP, "миллилитр", 5000, 0, 1500, 3500),
    ]


def test_build_records_after_end_are_ignored(first_start_storage: StorageManager):
    """ОСВ за сентябрь: октябрьские и ноябрьские записи не учитываются, и строк по ним нет."""
    # Действие
    report = build(first_start_storage, date(2026, 9, 1), date(2026, 9, 30))

    # Проверка
    assert rows(report) == [("Говядина", RESTAURANT, "грамм", 0, 5000, 2000, 3000)]


def test_build_end_day_record_is_counted_whatever_time(first_start_storage: StorageManager):
    """Конец включительно: запись от 31.10 в 23:00 попадает в приход периода, который заканчивается 31.10."""
    # Действие
    report = build(first_start_storage, date(2026, 10, 31), date(2026, 10, 31))

    # Проверка
    assert ("Говядина", WORKSHOP, "грамм", 0, 2000, 0, 2000) in rows(report)


def test_build_filter_uses_prototype(first_start_storage: StorageManager):
    """Условия запроса отбирают записи через Прототип: остаётся только говядина на обоих складах."""
    # Подготовка
    condition = FilterItemDto("nomenclature.name", FilterType.EQUALS, "Говядина")

    # Действие
    report = build(first_start_storage, date(2026, 10, 1), date(2026, 10, 31), condition)

    # Проверка
    assert rows(report) == [
        ("Говядина", RESTAURANT, "грамм", 3000, 3000, 4000, 2000),
        ("Говядина", WORKSHOP, "грамм", 0, 2000, 0, 2000),
    ]


def test_build_filter_by_nested_warehouse_name(first_start_storage: StorageManager):
    """Фильтр по вложенному пути warehouse.name оставляет строки одного склада."""
    # Подготовка
    condition = FilterItemDto("warehouse.name", FilterType.LIKE, "цеха")

    # Действие
    report = build(first_start_storage, date(2026, 10, 1), date(2026, 10, 31), condition)

    # Проверка
    assert [(row[0], row[1]) for row in rows(report)] == [("Молоко", WORKSHOP), ("Говядина", WORKSHOP)]


def test_build_without_start_begins_at_first_record(first_start_storage: StorageManager):
    """Без начала период открывается датой первой отобранной записи, поэтому остатки на начало нулевые."""
    # Действие
    report = build(first_start_storage, None, date(2026, 10, 31))

    # Проверка
    assert report.start == date(2026, 9, 1)
    assert all(row.opening == 0 for row in report.rows)
    assert rows(report)[0] == ("Говядина", RESTAURANT, "грамм", 0, 8000, 6000, 2000)


def test_build_without_end_ends_today(first_start_storage: StorageManager):
    """Без конца период закрывается сегодняшним днём."""
    # Действие
    report = build(first_start_storage, date(2026, 10, 1), None)

    # Проверка
    assert report.end == date.today()


def test_build_no_matching_records_returns_empty_report(first_start_storage: StorageManager):
    """Если фильтр ничего не отобрал, строк нет, а период без начала сводится к концу."""
    # Подготовка
    condition = FilterItemDto("nomenclature.name", FilterType.EQUALS, "Соль")

    # Действие
    report = build(first_start_storage, None, date(2026, 10, 31), condition)

    # Проверка
    assert report.rows == []
    assert report.start == date(2026, 10, 31)


def test_build_nomenclature_range_changed_after_records_raises(first_start_storage: StorageManager):
    """Единицу молока сменили на килограмм после проведения записей в литрах: сложить их нельзя, отчёт падает."""
    # Подготовка
    milk = next(item for item in first_start_storage.nomenclatures if item.name == "Молоко")
    milk.range = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие и проверка
    with pytest.raises(OperationException, match="Молоко"):
        _ = build(first_start_storage, date(2026, 10, 1), date(2026, 10, 31))
