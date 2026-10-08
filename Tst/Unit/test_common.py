from pathlib import Path
from typing import override

import pytest
from Src.Core.common import Common
from Src.Core.exception import OperationException
from Src.Models.settings_model import SettingsModel


class FieldsParentStub:
    """Родитель-заглушка: два свойства, константа, метод и приватное свойство."""

    LIMIT: int = 10

    @property
    def alpha(self) -> int:
        """Первое свойство родителя."""
        return 1

    @property
    def beta(self) -> int:
        """Второе свойство родителя."""
        return 2

    @property
    def _hidden(self) -> int:
        """Приватное свойство, не поле."""
        return 3

    def action(self) -> None:
        """Метод, не поле."""


class FieldsChildStub(FieldsParentStub):
    """Наследник-заглушка: переопределяет alpha и добавляет gamma."""

    @property
    @override
    def alpha(self) -> int:
        """Переопределённое свойство родителя."""
        return 10

    @property
    def gamma(self) -> int:
        """Собственное свойство наследника."""
        return 4


class FailingGetterStub:
    """Заглушка, у которой геттер падает: показывает, что get_fields его не вызывает."""

    @property
    def broken(self) -> int:
        """Свойство, чтение которого всегда бросает исключение."""
        raise RuntimeError("геттер не должен вызываться")


class EmptyStub:
    """Заглушка без свойств."""

    LIMIT: int = 1


def test_find_project_root_default_start_returns_dir_with_pyproject():
    """Без аргументов корень ищется от расположения модуля и содержит pyproject.toml."""
    # Подготовка

    # Действие
    root = Common.find_project_root()

    # Проверка
    assert (root / "pyproject.toml").is_file()
    assert root.is_absolute()


def test_find_project_root_default_start_ignores_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Смена текущего каталога не влияет на найденный корень."""
    # Подготовка
    expected = Common.find_project_root()
    monkeypatch.chdir(tmp_path)

    # Действие
    root = Common.find_project_root()

    # Проверка
    assert root == expected


def test_find_project_root_nested_start_returns_nearest_root(tmp_path: Path):
    """Из вложенного каталога возвращается ближайший каталог с pyproject.toml."""
    # Подготовка
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    # Действие
    root = Common.find_project_root(nested)

    # Проверка
    assert root == tmp_path.resolve()


def test_find_project_root_nested_roots_returns_innermost(tmp_path: Path):
    """При нескольких pyproject.toml по пути выбирается самый близкий к старту."""
    # Подготовка
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("", encoding="utf-8")

    # Действие
    root = Common.find_project_root(inner)

    # Проверка
    assert root == inner.resolve()


def test_find_project_root_start_is_file_returns_root(tmp_path: Path):
    """Старт можно задать файлом: поиск начинается с его каталога."""
    # Подготовка
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    start = tmp_path / "module.py"
    start.write_text("", encoding="utf-8")

    # Действие
    root = Common.find_project_root(start)

    # Проверка
    assert root == tmp_path.resolve()


def test_find_project_root_no_marker_raises_operation_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Если pyproject.toml нет ни в одном родительском каталоге, бросается OperationException."""
    # Подготовка
    # Проверка не зависит от окружения: у tmp_path подменяется проверка наличия маркера
    monkeypatch.setattr(Common, "_ROOT_MARKER", "missing-marker-file.toml")

    # Действие
    with pytest.raises(OperationException) as exc_info:
        Common.find_project_root(tmp_path)

    # Проверка
    assert "missing-marker-file.toml" in str(exc_info.value)


@pytest.mark.parametrize("file_name", ["", "   "])
def test_resolve_path_empty_name_returns_default_in_project_root(file_name: str):
    """Пустое имя означает файл по умолчанию в корне проекта."""
    # Подготовка

    # Действие
    path = Common.resolve_path(file_name, "settings.json")

    # Проверка
    assert path == Common.find_project_root() / "settings.json"


def test_resolve_path_empty_name_other_cwd_returns_default_in_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Файл по умолчанию не зависит от текущего каталога."""
    # Подготовка
    expected = Common.find_project_root() / "settings.json"
    monkeypatch.chdir(tmp_path)

    # Действие
    path = Common.resolve_path("", "settings.json")

    # Проверка
    assert path == expected


def test_resolve_path_relative_name_resolved_from_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Относительный путь отсчитывается от текущего каталога."""
    # Подготовка
    monkeypatch.chdir(tmp_path)

    # Действие
    path = Common.resolve_path("custom.json", "settings.json")

    # Проверка
    assert path == tmp_path.resolve() / "custom.json"


def test_resolve_path_absolute_name_returned_as_is(tmp_path: Path):
    """Абсолютный путь возвращается без изменений."""
    # Подготовка
    file_path = tmp_path / "custom.json"

    # Действие
    path = Common.resolve_path(str(file_path), "settings.json")

    # Проверка
    assert path == file_path.resolve()


def test_resolve_path_name_with_spaces_around_stripped(tmp_path: Path):
    """Пробелы по краям переданного пути отбрасываются."""
    # Подготовка
    file_path = tmp_path / "custom.json"

    # Действие
    path = Common.resolve_path(f"  {file_path}  ", "settings.json")

    # Проверка
    assert path == file_path.resolve()


def test_get_fields_class_returns_public_property_names():
    """Для класса возвращаются имена публичных свойств."""
    # Подготовка

    # Действие
    fields = Common.get_fields(FieldsParentStub)

    # Проверка
    assert fields == ["alpha", "beta"]


def test_get_fields_instance_returns_same_as_class():
    """Для экземпляра результат тот же, что для его класса."""
    # Подготовка
    instance = FieldsChildStub()

    # Действие
    from_instance = Common.get_fields(instance)
    from_class = Common.get_fields(FieldsChildStub)

    # Проверка
    assert from_instance == from_class


def test_get_fields_constants_methods_private_excluded():
    """Константы, методы и приватные свойства в поля не попадают."""
    # Подготовка

    # Действие
    fields = Common.get_fields(FieldsParentStub)

    # Проверка
    assert "LIMIT" not in fields
    assert "action" not in fields
    assert "_hidden" not in fields


def test_get_fields_inherited_properties_listed_before_own():
    """Поля базового класса идут раньше полей наследника."""
    # Подготовка

    # Действие
    fields = Common.get_fields(FieldsChildStub)

    # Проверка
    assert fields == ["alpha", "beta", "gamma"]


def test_get_fields_overridden_property_listed_once_at_base_position():
    """Переопределённое свойство не дублируется и остаётся на месте первого объявления."""
    # Подготовка

    # Действие
    fields = Common.get_fields(FieldsChildStub)

    # Проверка
    assert fields.count("alpha") == 1
    assert fields.index("alpha") == 0


def test_get_fields_exclude_names_removed():
    """Имена из exclude в результат не попадают."""
    # Подготовка

    # Действие
    fields = Common.get_fields(FieldsChildStub, exclude=("beta", "gamma"))

    # Проверка
    assert fields == ["alpha"]


def test_get_fields_instance_with_failing_getter_does_not_call_it():
    """Геттеры не вызываются, поэтому падающее свойство не мешает получить список."""
    # Подготовка
    instance = FailingGetterStub()

    # Действие
    fields = Common.get_fields(instance)

    # Проверка
    assert fields == ["broken"]


def test_get_fields_class_without_properties_returns_empty_list():
    """У класса без свойств список полей пуст."""
    # Подготовка

    # Действие
    fields = Common.get_fields(EmptyStub)

    # Проверка
    assert fields == []


def test_get_fields_settings_model_returns_expected_fields():
    """Контракт: поля настроек перечислены в порядке объявления, id идёт первым."""
    # Подготовка

    # Действие
    fields = Common.get_fields(SettingsModel)

    # Проверка
    assert fields == ["id", "organization", "boss_name", "account_name", "is_first_start"]
