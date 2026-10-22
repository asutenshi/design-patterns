from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException
from Src.Logics.datetime_converter import DatetimeConverter


# Подготовка
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 10, 22, 12, 30, 15, tzinfo=UTC), "2026-10-22T12:30:15+00:00"),
        (datetime(2026, 10, 22, 12, 30, tzinfo=timezone(timedelta(hours=7))), "2026-10-22T12:30:00+07:00"),
        (date(2026, 10, 22), "2026-10-22"),
    ],
    ids=["datetime_utc", "datetime_offset", "date"],
)
def test_convert_date_returns_field_with_iso_string(value: date, expected: str):
    """Дата и дата со временем записываются строкой ISO 8601, часовой пояс сохраняется."""
    # Подготовка
    converter = DatetimeConverter()

    # Действие
    result = converter.convert("created_at", value)

    # Проверка
    assert isinstance(converter, AbstractConverter)
    assert result == {"created_at": expected}


def test_convert_date_result_is_restored_by_fromisoformat():
    """Из строки результата восстанавливается исходная дата со временем."""
    # Подготовка
    value = datetime(2026, 10, 22, 12, 30, 15, 500, tzinfo=UTC)

    # Действие
    result = DatetimeConverter().convert("created_at", value)

    # Проверка
    assert datetime.fromisoformat(str(result["created_at"])) == value


# Подготовка
@pytest.mark.parametrize("value", ["2026-10-22", 20261022, None], ids=["str", "int", "none"])
def test_convert_not_date_raises(value: object):
    """Строка, число и None — не даты, их обрабатывает конвертер простых значений."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DatetimeConverter().convert("created_at", value)


def test_convert_invalid_field_raises():
    """Наименование поля должно быть непустой строкой."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = DatetimeConverter().convert(" ", date(2026, 10, 22))
