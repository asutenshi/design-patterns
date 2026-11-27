from datetime import datetime

import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Models.log_model import LogModel

# Дата события для тестов
PERIOD = datetime(2026, 11, 26, 12, 30, 0)


def test_init_valid_values_sets_fields():
    """Запись лога сохраняет дату, подсистему, уровень и очищенное сообщение."""
    # Действие
    entry = LogModel(PERIOD, LogSubsystem.CRUD, LogLevel.INFO, "  Создана номенклатура  ")

    # Проверка
    assert entry.period == PERIOD
    assert entry.subsystem is LogSubsystem.CRUD
    assert entry.level is LogLevel.INFO
    assert entry.message == "Создана номенклатура"


# Подготовка
@pytest.mark.parametrize(
    ("period", "subsystem", "level", "message"),
    [
        ("2026-11-26T12:30:00", LogSubsystem.CRUD, LogLevel.INFO, "ok"),
        (PERIOD, "CRUD", LogLevel.INFO, "ok"),
        (PERIOD, LogSubsystem.CRUD, "INFO", "ok"),
        (PERIOD, LogSubsystem.CRUD, LogLevel.INFO, "   "),
        (PERIOD, LogSubsystem.CRUD, LogLevel.INFO, 123),
    ],
)
def test_init_invalid_arguments_raises(period: object, subsystem: object, level: object, message: object):
    """Неверный тип любого поля или пустое сообщение отклоняются исключением ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = LogModel(period, subsystem, level, message)  # pyright: ignore[reportArgumentType]


def test_from_dict_valid_data_creates_log_model():
    """Фабричный метод восстанавливает запись лога из словаря с ISO-датой и строками перечислений."""
    # Подготовка
    data: dict[str, object] = {
        "period": "2026-11-26T12:30:00",
        "subsystem": "WEB",
        "level": "ERROR",
        "message": "Маршрут не найден",
    }

    # Действие
    entry = LogModel.from_dict(data)

    # Проверка
    assert entry.period == PERIOD
    assert entry.subsystem is LogSubsystem.WEB
    assert entry.level is LogLevel.ERROR
    assert entry.message == "Маршрут не найден"


# Подготовка
@pytest.mark.parametrize(
    "data",
    [
        {"subsystem": "WEB", "level": "INFO", "message": "ok"},
        {"period": "не дата", "subsystem": "WEB", "level": "INFO", "message": "ok"},
        {"period": "2026-11-26T12:30:00", "subsystem": "UNKNOWN", "level": "INFO", "message": "ok"},
        {"period": "2026-11-26T12:30:00", "subsystem": "WEB", "level": "WARN", "message": "ok"},
    ],
)
def test_from_dict_invalid_data_raises(data: dict[str, object]):
    """Недостающее поле, неверная дата или неизвестное значение перечисления вызывают ошибку."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = LogModel.from_dict(data)
