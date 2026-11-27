from datetime import datetime
from typing import override

import pytest
from fastapi.testclient import TestClient
from Src.Core.abstract_observer import AbstractObserver
from Src.Core.entity_type import EntityType
from Src.Core.event_type import EventType
from Src.Core.exception import ArgumentsException
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Core.response_format import ResponseFormat
from Src.Dtos.event_dto import EventDto
from Src.Logics.entity_service import EntityService
from Src.Logics.logger_manager import LoggerManager
from Src.Logics.observer import Observer
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager
from Src.main import app
from Src.Models.transaction_model import TransactionModel


class _EventCollector(AbstractObserver):
    """Тестовый наблюдатель, собирающий все опубликованные события."""

    def __init__(self) -> None:
        """Создаёт пустой список событий."""
        self.events: list[EventDto] = []

    @override
    def handle(self, event: EventDto) -> None:
        """Добавляет событие в список."""
        self.events.append(event)


def test_storage_add_transaction_notifies_warehouse_event(first_start_storage: StorageManager):
    """Проведение складской операции отправляет событие TRANSACTION_ADDED в подсистеме WAREHOUSE."""
    # Подготовка
    collector = _EventCollector()
    Observer.add(collector)
    nomenclature = first_start_storage.nomenclatures[0]
    warehouse = first_start_storage.warehouses[0]
    transaction = TransactionModel(nomenclature, warehouse, nomenclature.range, 5, datetime(2026, 11, 26, 10, 0))

    # Действие
    first_start_storage.add_transaction(transaction)

    # Проверка
    assert len(collector.events) == 1
    event = collector.events[0]
    assert event.event_type is EventType.TRANSACTION_ADDED
    assert event.subsystem is LogSubsystem.WAREHOUSE
    assert event.level is LogLevel.INFO
    assert event.payload is transaction


def test_settings_update_valid_data_updates_in_place_and_notifies(load_settings):
    """Обновление настроек меняет модель на месте и отправляет событие SETTINGS_CHANGED с уровнем INFO."""
    # Подготовка
    load_settings(True)
    manager = SettingsManager()
    original_ref = manager.settings
    collector = _EventCollector()
    Observer.add(collector)

    # Действие
    updated = manager.update({"boss_name": "Сидоров Пётр Иванович", "response_format": "csv"})

    # Проверка
    assert updated is original_ref
    assert manager.settings.boss_name == "Сидоров Пётр Иванович"
    assert manager.settings.response_format is ResponseFormat.CSV
    assert len(collector.events) == 1
    event = collector.events[0]
    assert event.event_type is EventType.SETTINGS_CHANGED
    assert event.subsystem is LogSubsystem.SETTINGS
    assert event.level is LogLevel.INFO


def test_settings_update_invalid_data_preserves_state_and_notifies_error(load_settings):
    """Некорректное обновление не меняет настройки и отправляет событие SETTINGS_CHANGED с уровнем ERROR."""
    # Подготовка
    load_settings(True)
    manager = SettingsManager()
    collector = _EventCollector()
    Observer.add(collector)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = manager.update({"response_format": "unknown"})

    assert manager.settings.response_format is ResponseFormat.TXT
    assert len(collector.events) == 1
    assert collector.events[0].level is LogLevel.ERROR
    assert collector.events[0].subsystem is LogSubsystem.SETTINGS


def test_web_middleware_logs_get_as_debug_and_error_as_error():
    """HTTP-middleware логирует успешный GET с уровнем DEBUG, а ответ 404 с уровнем ERROR."""
    # Подготовка
    with TestClient(app) as client:
        logger = LoggerManager()
        logger.clear()

        # Действие
        ok_response = client.get("/api/get_report_formats")
        missing_response = client.get("/api/entities/warehouse/00000000-0000-0000-0000-000000000000")

        # Проверка
        assert ok_response.status_code == 200
        assert missing_response.status_code == 404
        web_logs = [entry for entry in logger.logs if entry.subsystem is LogSubsystem.WEB]
        assert len(web_logs) == 2
        assert web_logs[0].level is LogLevel.DEBUG
        assert "/api/get_report_formats" in web_logs[0].message
        assert web_logs[1].level is LogLevel.ERROR
        assert "404" in web_logs[1].message


def test_entity_service_crud_notifies_observer(first_start_storage: StorageManager):
    """Операции create, put, patch и delete публикуют CRUD-события с самой сущностью в payload."""
    # Подготовка
    service = EntityService(first_start_storage)
    collector = _EventCollector()
    Observer.add(collector)

    # Действие
    created = service.create(EntityType.WAREHOUSE, {"name": "Тестовый склад"})
    service.patch(EntityType.WAREHOUSE, created.id, {"name": "Обновлённый склад"})
    service.put(EntityType.WAREHOUSE, created.id, {"name": "Заменённый склад"})
    service.delete(EntityType.WAREHOUSE, created.id)

    # Проверка
    assert [event.event_type for event in collector.events] == [
        EventType.ENTITY_CREATED,
        EventType.ENTITY_UPDATED,
        EventType.ENTITY_UPDATED,
        EventType.ENTITY_DELETED,
    ]
    assert all(event.subsystem is LogSubsystem.CRUD for event in collector.events)
    assert all(event.level is LogLevel.INFO for event in collector.events)
    assert all(event.payload is created for event in collector.events)
