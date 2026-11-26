from datetime import datetime
from pathlib import Path

from Src.Core.event_type import EventType
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Dtos.event_dto import EventDto
from Src.Logics.logger_manager import LoggerManager
from Src.Logics.observer import Observer


def test_singleton_returns_same_instance():
    """Повторные обращения к LoggerManager возвращают один и тот же экземпляр."""
    # Действие
    first = LoggerManager()
    second = LoggerManager()

    # Проверка
    assert first is second


def test_load_subscribes_to_observer_and_records_events():
    """После load() менеджер получает события от Observer и сохраняет их как LogModel."""
    # Подготовка
    manager = LoggerManager()
    manager.load()
    period = datetime(2026, 11, 26, 15, 0, 0)
    event = EventDto(
        EventType.ENTITY_CREATED,
        LogSubsystem.CRUD,
        "Создана номенклатура Говядина",
        level=LogLevel.INFO,
        period=period,
    )

    # Действие
    Observer.notify(event)

    # Проверка
    assert manager.is_loaded is True
    assert len(manager.logs) == 1
    entry = manager.logs[0]
    assert entry.period == period
    assert entry.subsystem is LogSubsystem.CRUD
    assert entry.level is LogLevel.INFO
    assert entry.message == "Создана номенклатура Говядина"


def test_logs_returns_copy():
    """Изменение возвращённого списка logs не меняет внутреннее хранилище менеджера."""
    # Подготовка
    manager = LoggerManager()
    manager.load()
    Observer.notify(EventDto(EventType.WEB_REQUEST, LogSubsystem.WEB, "GET /docs"))

    # Действие
    snapshot = manager.logs
    snapshot.clear()

    # Проверка
    assert len(manager.logs) == 1


def test_save_writes_content_to_file(tmp_path: Path):
    """Метод save() записывает переданное содержимое лога в указанный файл UTF-8."""
    # Подготовка
    manager = LoggerManager()
    target = tmp_path / "logs" / "app.txt"

    # Действие
    saved_path = manager.save(str(target), "Запись лога\n")

    # Проверка
    assert saved_path == target
    assert target.read_text(encoding="utf-8") == "Запись лога\n"
