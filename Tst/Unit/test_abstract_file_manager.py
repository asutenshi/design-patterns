from abc import ABC
from typing import Any, Self, override

import pytest
from Src.Core.abstract_file_manager import AbstractFileManager
from Src.Core.exception import OperationException


class _StubFileManager(AbstractFileManager):
    """Менеджер для проверки базового класса: журналирует вызовы и умеет падать.

    Не Singleton: Singleton задают конкретные менеджеры.
    """

    # Журнал вызовов в порядке их выполнения
    calls: list[str]
    # Результат convert: копия сырых данных
    converted: dict[str, Any]
    # На каком шаге упасть: "read", "convert" или "" (не падать)
    fail_on: str

    def __new__(cls) -> Self:
        instance = super().__new__(cls)
        instance._initialize()
        return instance

    @override
    def _initialize(self) -> None:
        super()._initialize()
        self.calls = ["initialize"]
        self.converted = {}
        self.fail_on = ""

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        self.calls.append("read")
        if self.fail_on == "read":
            raise OperationException("Не удалось прочитать")
        return {"file_name": file_name}

    @override
    def convert(self) -> None:
        self.calls.append("convert")
        if self.fail_on == "convert":
            raise OperationException("Не удалось преобразовать")
        self.converted = dict(self._data)


class _WithoutConvertManager(AbstractFileManager, ABC):
    """Наследник без convert: остаётся абстрактным."""

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        return {}


class _WithoutReadManager(AbstractFileManager, ABC):
    """Наследник без _read: остаётся абстрактным."""

    @override
    def convert(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Абстрактность
# ---------------------------------------------------------------------------


def test_init_abstract_file_manager_directly_raises_type_error():
    """Напрямую создать AbstractFileManager нельзя."""
    # Действие и проверка
    with pytest.raises(TypeError):
        AbstractFileManager()  # pyright: ignore[reportAbstractUsage]


def test_init_subclass_without_convert_raises_type_error():
    """Наследник, не реализовавший convert, не создаётся."""
    # Действие и проверка
    with pytest.raises(TypeError):
        _WithoutConvertManager()  # pyright: ignore[reportAbstractUsage]


def test_init_subclass_without_read_raises_type_error():
    """Наследник, не реализовавший _read, не создаётся."""
    # Действие и проверка
    with pytest.raises(TypeError):
        _WithoutReadManager()  # pyright: ignore[reportAbstractUsage]


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


def test_load_success_calls_read_then_convert_in_order():
    """load сначала читает данные, затем преобразует их."""
    # Подготовка
    manager = _StubFileManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.calls == ["initialize", "read", "convert"]


def test_load_success_sets_is_loaded_true():
    """После успешной загрузки is_loaded равен True."""
    # Подготовка
    manager = _StubFileManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.is_loaded is True


# Подготовка
@pytest.mark.parametrize("file_name", ["", "settings.json", "data/other.json"])
def test_load_file_name_is_passed_to_read_and_data_reaches_convert(file_name: str):
    """Имя файла уходит в _read, а прочитанные данные доступны в convert."""
    # Подготовка
    manager = _StubFileManager()

    # Действие
    manager.load(file_name)

    # Проверка
    assert manager.converted == {"file_name": file_name}


def test_load_read_fails_raises_and_is_loaded_stays_false():
    """Если чтение упало, исключение пробрасывается и is_loaded остаётся False."""
    # Подготовка
    manager = _StubFileManager()
    manager.fail_on = "read"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load()
    assert manager.is_loaded is False


def test_load_read_fails_convert_is_not_called():
    """Если чтение упало, convert не вызывается."""
    # Подготовка
    manager = _StubFileManager()
    manager.fail_on = "read"

    # Действие
    with pytest.raises(OperationException):
        manager.load()

    # Проверка
    assert "convert" not in manager.calls


def test_load_convert_fails_raises_and_is_loaded_stays_false():
    """Если преобразование упало, исключение пробрасывается и is_loaded остаётся False."""
    # Подготовка
    manager = _StubFileManager()
    manager.fail_on = "convert"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load()
    assert manager.is_loaded is False


def test_load_repeated_after_success_failure_resets_is_loaded():
    """Неудачная повторная загрузка сбрасывает флаг, выставленный предыдущей успешной."""
    # Подготовка
    manager = _StubFileManager()
    manager.load()
    manager.fail_on = "convert"

    # Действие
    with pytest.raises(OperationException):
        manager.load()

    # Проверка
    assert manager.is_loaded is False


def test_load_after_failed_load_succeeds_when_cause_is_gone():
    """После неудачной загрузки повторная успешная выставляет is_loaded в True."""
    # Подготовка
    manager = _StubFileManager()
    manager.fail_on = "read"
    with pytest.raises(OperationException):
        manager.load()
    manager.fail_on = ""

    # Действие
    manager.load()

    # Проверка
    assert manager.is_loaded is True
