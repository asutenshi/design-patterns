from datetime import datetime

import pytest
from Src.Core.event_type import EventType
from Src.Core.exception import ArgumentsException
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Dtos.event_dto import EventDto

# Фиксированное время события для тестов
PERIOD = datetime(2026, 11, 26, 14, 0, 0)


def test_init_defaults_sets_info_level_and_current_period():
    """Без явных level, period и payload событие получает уровень INFO, текущее время и пустую нагрузку."""
    # Подготовка
    before = datetime.now()

    # Действие
    event = EventDto(EventType.ENTITY_CREATED, LogSubsystem.CRUD, "Создан склад")
    after = datetime.now()

    # Проверка
    assert event.event_type is EventType.ENTITY_CREATED
    assert event.subsystem is LogSubsystem.CRUD
    assert event.level is LogLevel.INFO
    assert event.message == "Создан склад"
    assert before <= event.period <= after
    assert event.payload is None


def test_init_explicit_values_sets_all_fields():
    """Явно переданные уровень, дата и полезная нагрузка сохраняются без изменений."""
    # Подготовка
    payload = {"entity_id": "abc"}

    # Действие
    event = EventDto(
        EventType.WEB_ERROR,
        LogSubsystem.WEB,
        "Ошибка запроса",
        level=LogLevel.ERROR,
        period=PERIOD,
        payload=payload,
    )

    # Проверка
    assert event.level is LogLevel.ERROR
    assert event.period == PERIOD
    assert event.payload is payload


# Подготовка
@pytest.mark.parametrize(
    ("event_type", "subsystem", "message", "level", "period"),
    [
        ("entity_created", LogSubsystem.CRUD, "ok", LogLevel.INFO, PERIOD),
        (EventType.ENTITY_CREATED, "CRUD", "ok", LogLevel.INFO, PERIOD),
        (EventType.ENTITY_CREATED, LogSubsystem.CRUD, "   ", LogLevel.INFO, PERIOD),
        (EventType.ENTITY_CREATED, LogSubsystem.CRUD, "ok", "INFO", PERIOD),
        (EventType.ENTITY_CREATED, LogSubsystem.CRUD, "ok", LogLevel.INFO, "2026-11-26"),
    ],
)
def test_init_invalid_arguments_raises(
    event_type: object, subsystem: object, message: object, level: object, period: object
):
    """Некорректные значения полей события отклоняются исключением ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = EventDto(event_type, subsystem, message, level=level, period=period)  # pyright: ignore[reportArgumentType]
