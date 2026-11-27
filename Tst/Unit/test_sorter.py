from datetime import datetime

import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Core.sort_order import SortOrder
from Src.Dtos.sort_dto import SortDto
from Src.Logics.sorter import Sorter
from Src.Logics.storage_manager import StorageManager
from Src.Models.log_model import LogModel


def _sample_logs() -> list[LogModel]:
    """Возвращает три записи лога в произвольном порядке для тестов сортировки."""
    return [
        LogModel(datetime(2026, 11, 26, 12, 0), LogSubsystem.WEB, LogLevel.INFO, "Вторая"),
        LogModel(datetime(2026, 11, 26, 10, 0), LogSubsystem.CRUD, LogLevel.ERROR, "Первая"),
        LogModel(datetime(2026, 11, 26, 14, 0), LogSubsystem.SETTINGS, LogLevel.DEBUG, "Третья"),
    ]


def test_sort_by_period_asc_and_desc_returns_new_list():
    """Сортировка по дате работает в обоих направлениях и не изменяет исходный список."""
    # Подготовка
    logs = _sample_logs()
    original_order = list(logs)
    sorter = Sorter()

    # Действие
    asc = sorter.sort(logs, SortDto("period", SortOrder.ASC))
    desc = sorter.sort(logs, SortDto("period", SortOrder.DESC))

    # Проверка
    assert logs == original_order
    assert [entry.message for entry in asc] == ["Первая", "Вторая", "Третья"]
    assert [entry.message for entry in desc] == ["Третья", "Вторая", "Первая"]


def test_sort_by_enum_field_compares_enum_values():
    """Сортировка по перечислению сравнивает его строковые значения."""
    # Подготовка
    logs = _sample_logs()
    sorter = Sorter()

    # Действие
    by_level = sorter.sort(logs, SortDto("level", SortOrder.ASC))
    by_subsystem = sorter.sort(logs, SortDto("subsystem", SortOrder.DESC))

    # Проверка
    assert [entry.level for entry in by_level] == [LogLevel.DEBUG, LogLevel.ERROR, LogLevel.INFO]
    assert [entry.subsystem for entry in by_subsystem] == [
        LogSubsystem.WEB,
        LogSubsystem.SETTINGS,
        LogSubsystem.CRUD,
    ]


def test_sort_by_nested_field_works_on_domain_models(first_start_storage: StorageManager):
    """Сортировщик работает с любыми доменными моделями по вложенному пути через точку."""
    # Подготовка
    sorter = Sorter()
    transactions = first_start_storage.transactions

    # Действие
    sorted_tx = sorter.sort(transactions, SortDto("warehouse.name", SortOrder.ASC))

    # Проверка
    names = [tx.warehouse.name for tx in sorted_tx]
    assert names == sorted(names)


def test_sort_unknown_field_raises():
    """Неизвестное или приватное поле отклоняется исключением ArgumentsException."""
    # Подготовка
    sorter = Sorter()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = sorter.sort(_sample_logs(), SortDto("_message", SortOrder.ASC))


def test_sort_collection_path_raises(first_start_storage: StorageManager):
    """Путь через коллекцию с несколькими значениями не даёт однозначного ключа сортировки."""
    # Подготовка
    sorter = Sorter()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = sorter.sort(first_start_storage.recipes, SortDto("items.quantity", SortOrder.ASC))


def test_sort_incomparable_values_raises():
    """Несравнимые значения поля вроде None и числа приводят к ArgumentsException."""
    # Подготовка
    class _Item:
        """Учебная модель с необязательным числом."""

        def __init__(self, value: int | None) -> None:
            """Сохраняет значение."""
            self._value = value

        @property
        def value(self) -> int | None:
            """Возвращает значение."""
            return self._value

    sorter = Sorter()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = sorter.sort([_Item(1), _Item(None)], SortDto("value", SortOrder.ASC))
