import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from Src.Core.abstract_manager import AbstractManager
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager


def _reset_manager_instances() -> None:
    """Сбрасывает единственные экземпляры у всех подклассов AbstractManager."""
    stack: list[type] = [AbstractManager]
    while stack:
        cls = stack.pop()
        stack.extend(cls.__subclasses__())
        if "_instance" in vars(cls):
            cls._instance = None  # pyright: ignore[reportAttributeAccessIssue, reportPrivateUsage]


@pytest.fixture(autouse=True)
def reset_manager_instances() -> Iterator[None]:
    """Сбрасывает экземпляры менеджеров до и после каждого теста.

    Менеджеры — синглтоны, и без сброса состояние одного теста попадало бы в другой.
    """
    _reset_manager_instances()
    yield
    _reset_manager_instances()


@pytest.fixture
def load_settings(tmp_path: Path) -> Callable[[bool], None]:
    """Возвращает функцию, которая загружает в SettingsManager настройки с заданным флагом первого запуска."""

    def load(is_first_start: bool) -> None:
        data = {
            "organization": {
                "name": "Ромашка",
                "inn": "1234567894",
                "bic": "123456789",
                "account": "12345678901234567890",
                "ownership_form": "ООО",
            },
            "boss_name": "Иванов Иван Иванович",
            "account_name": "Петрова Анна Александровна",
            "is_first_start": is_first_start,
        }
        path = tmp_path / "settings.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        SettingsManager().load(str(path))

    return load


@pytest.fixture
def first_start_storage(load_settings: Callable[[bool], None]) -> StorageManager:
    """Хранилище, загруженное при первом запуске."""
    load_settings(True)
    storage = StorageManager()
    storage.load()
    return storage
