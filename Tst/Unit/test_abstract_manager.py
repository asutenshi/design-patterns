from abc import ABC
from typing import Any, override

import pytest
from Src.Core.abstract_manager import AbstractManager
from Src.Core.exception import OperationException


class _StubManager(AbstractManager):
    """Менеджер для проверки базового класса: журналирует вызовы и умеет падать."""

    # Журнал вызовов в порядке их выполнения
    calls: list[str]
    # Результат convert: копия сырых данных
    converted: dict[str, Any]
    # На каком шаге упасть: "read", "convert" или "" (не падать)
    fail_on: str

    @override
    def _initialize(self) -> None:
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


class _ChildManager(_StubManager):
    """Наследник конкретного менеджера: должен получить собственный экземпляр."""


class _OtherManager(AbstractManager):
    """Второй независимый менеджер."""

    converted: dict[str, Any]

    @override
    def _initialize(self) -> None:
        self.converted = {}

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        return {"other": True}

    @override
    def convert(self) -> None:
        self.converted = dict(self._data)


class _FailingInitManager(AbstractManager):
    """Менеджер, у которого падает хук _initialize."""

    @override
    def _initialize(self) -> None:
        raise OperationException("Не удалось подготовить состояние")

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        return {}

    @override
    def convert(self) -> None:
        pass


class _WithoutConvertManager(AbstractManager, ABC):
    """Наследник без convert: остаётся абстрактным."""

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        return {}


class _WithoutReadManager(AbstractManager, ABC):
    """Наследник без _read: остаётся абстрактным."""

    @override
    def convert(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Абстрактность
# ---------------------------------------------------------------------------


def test_init_abstract_manager_directly_raises_type_error():
    """Напрямую создать AbstractManager нельзя."""
    # Действие и проверка
    with pytest.raises(TypeError):
        AbstractManager()  # pyright: ignore[reportAbstractUsage]


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
# Singleton
# ---------------------------------------------------------------------------


def test_new_same_class_returns_same_instance():
    """Повторное создание одного класса возвращает тот же экземпляр."""
    # Подготовка
    first = _StubManager()

    # Действие
    second = _StubManager()

    # Проверка
    assert first is second


def test_new_different_classes_return_different_instances():
    """Разные менеджеры получают разные экземпляры."""
    # Действие
    stub = _StubManager()
    other = _OtherManager()

    # Проверка
    assert isinstance(stub, _StubManager)
    assert isinstance(other, _OtherManager)
    assert stub is not other


def test_new_subclass_of_manager_returns_own_instance():
    """Наследник конкретного менеджера не получает экземпляр родителя."""
    # Подготовка
    parent = _StubManager()

    # Действие
    child = _ChildManager()

    # Проверка
    assert child is not parent
    assert type(child) is _ChildManager


def test_new_data_is_not_shared_between_managers():
    """Сырые данные одного менеджера не видны другому."""
    # Подготовка
    stub = _StubManager()
    other = _OtherManager()

    # Действие
    stub.load("a.json")
    other.load()

    # Проверка
    assert stub.converted == {"file_name": "a.json"}
    assert other.converted == {"other": True}


# ---------------------------------------------------------------------------
# Хук _initialize
# ---------------------------------------------------------------------------


def test_new_initialize_hook_called_once_for_repeated_creation():
    """Хук _initialize вызывается один раз, сколько бы раз ни создавали менеджер."""
    # Действие
    _StubManager()
    _StubManager()
    manager = _StubManager()

    # Проверка
    assert manager.calls == ["initialize"]


def test_new_initialize_hook_failure_raises_and_instance_is_not_registered():
    """Если хук упал, исключение пробрасывается, а полусозданный экземпляр не сохраняется."""
    # Действие и проверка
    with pytest.raises(OperationException):
        _FailingInitManager()
    assert _FailingInitManager not in AbstractManager._instances  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(OperationException):
        _FailingInitManager()


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


def test_is_loaded_assignment_raises_attribute_error():
    """Флаг is_loaded доступен только для чтения."""
    # Подготовка
    manager = _StubManager()

    # Действие и проверка
    with pytest.raises(AttributeError):
        manager.is_loaded = True  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


def test_load_success_calls_read_then_convert_in_order():
    """load сначала читает данные, затем преобразует их."""
    # Подготовка
    manager = _StubManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.calls == ["initialize", "read", "convert"]


def test_load_success_sets_is_loaded_true():
    """После успешной загрузки is_loaded равен True."""
    # Подготовка
    manager = _StubManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.is_loaded is True


# Подготовка
@pytest.mark.parametrize("file_name", ["", "settings.json", "data/other.json"])
def test_load_file_name_is_passed_to_read_and_data_reaches_convert(file_name: str):
    """Имя источника уходит в _read, а прочитанные данные доступны в convert."""
    # Подготовка
    manager = _StubManager()

    # Действие
    manager.load(file_name)

    # Проверка
    assert manager.converted == {"file_name": file_name}


def test_load_read_fails_raises_and_is_loaded_stays_false():
    """Если чтение упало, исключение пробрасывается и is_loaded остаётся False."""
    # Подготовка
    manager = _StubManager()
    manager.fail_on = "read"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load()
    assert manager.is_loaded is False


def test_load_read_fails_convert_is_not_called():
    """Если чтение упало, convert не вызывается."""
    # Подготовка
    manager = _StubManager()
    manager.fail_on = "read"

    # Действие
    with pytest.raises(OperationException):
        manager.load()

    # Проверка
    assert "convert" not in manager.calls


def test_load_convert_fails_raises_and_is_loaded_stays_false():
    """Если преобразование упало, исключение пробрасывается и is_loaded остаётся False."""
    # Подготовка
    manager = _StubManager()
    manager.fail_on = "convert"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load()
    assert manager.is_loaded is False


def test_load_repeated_after_success_failure_resets_is_loaded():
    """Неудачная повторная загрузка сбрасывает флаг, выставленный предыдущей успешной."""
    # Подготовка
    manager = _StubManager()
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
    manager = _StubManager()
    manager.fail_on = "read"
    with pytest.raises(OperationException):
        manager.load()
    manager.fail_on = ""

    # Действие
    manager.load()

    # Проверка
    assert manager.is_loaded is True