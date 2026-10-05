from abc import ABC
from typing import Self, override

import pytest
from Src.Core.abstract_manager import AbstractManager


class _StubManager(AbstractManager):
    """Менеджер для проверки базового класса. Не Singleton: Singleton задают конкретные менеджеры."""

    def __new__(cls) -> Self:
        instance = super().__new__(cls)
        instance._initialize()
        return instance

    @override
    def load(self) -> None:
        self._is_loaded = True


class _WithoutLoadManager(AbstractManager, ABC):
    """Наследник без load: остаётся абстрактным."""


# ---------------------------------------------------------------------------
# Абстрактность
# ---------------------------------------------------------------------------


def test_init_abstract_manager_directly_raises_type_error():
    """Напрямую создать AbstractManager нельзя."""
    # Действие и проверка
    with pytest.raises(TypeError):
        AbstractManager()  # pyright: ignore[reportAbstractUsage]


def test_init_subclass_without_load_raises_type_error():
    """Наследник, не реализовавший load, не создаётся."""
    # Действие и проверка
    with pytest.raises(TypeError):
        _WithoutLoadManager()  # pyright: ignore[reportAbstractUsage]


# ---------------------------------------------------------------------------
# is_loaded
# ---------------------------------------------------------------------------


def test_is_loaded_new_manager_is_false():
    """Новый менеджер не загружен."""
    # Подготовка
    manager = _StubManager()

    # Действие
    result = manager.is_loaded

    # Проверка
    assert result is False


def test_is_loaded_after_load_is_true():
    """После load флаг is_loaded отражает состояние, выставленное наследником."""
    # Подготовка
    manager = _StubManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.is_loaded is True


def test_is_loaded_assignment_raises_attribute_error():
    """Флаг is_loaded доступен только для чтения."""
    # Подготовка
    manager = _StubManager()

    # Действие и проверка
    with pytest.raises(AttributeError):
        manager.is_loaded = True  # pyright: ignore[reportAttributeAccessIssue]
