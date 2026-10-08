import json
from pathlib import Path
from typing import Any

import pytest
from Src.Core.common import Common
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.ownership_form import OwnershipForm
from Src.Logics.settings_manager import SettingsManager


@pytest.fixture
def settings_data() -> dict[str, Any]:
    """Корректное содержимое файла настроек. Каждый тест получает свою копию."""
    return {
        "organization": {
            "name": "Ромашка",
            "inn": "1234567894",
            "bic": "123456789",
            "account": "12345678901234567890",
            "ownership_form": "ООО",
        },
        "boss_name": "Иванов Иван Иванович",
        "account_name": "Петрова Анна Александровна",
        "is_first_start": True,
    }


def _write_json(directory: Path, data: object, name: str = "settings.json") -> str:
    """Записывает data в JSON-файл и возвращает путь к нему."""
    path = directory / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# load: успешная загрузка
# ---------------------------------------------------------------------------


def test_load_valid_file_converts_organization(tmp_path: Path, settings_data: dict[str, Any]):
    """Карточка организации собирается из данных файла."""
    # Подготовка
    manager = SettingsManager()

    # Действие
    manager.load(_write_json(tmp_path, settings_data))

    # Проверка
    organization = manager.settings.organization
    assert organization.name == "Ромашка"
    assert organization.inn == "1234567894"
    assert organization.bic == "123456789"
    assert organization.account == "12345678901234567890"
    assert organization.ownership_form == OwnershipForm.LLC


def test_load_valid_file_converts_responsible_persons(tmp_path: Path, settings_data: dict[str, Any]):
    """Директор и главный бухгалтер берутся из данных файла."""
    # Подготовка
    manager = SettingsManager()

    # Действие
    manager.load(_write_json(tmp_path, settings_data))

    # Проверка
    assert manager.settings.boss_name == "Иванов Иван Иванович"
    assert manager.settings.account_name == "Петрова Анна Александровна"


# Подготовка
@pytest.mark.parametrize("is_first_start", [True, False])
def test_load_is_first_start_value_is_taken_from_file(tmp_path: Path, settings_data: dict[str, Any], is_first_start: bool):
    """Флаг первого запуска берётся из файла как есть."""
    # Подготовка
    manager = SettingsManager()
    settings_data["is_first_start"] = is_first_start

    # Действие
    manager.load(_write_json(tmp_path, settings_data))

    # Проверка
    assert manager.settings.is_first_start is is_first_start


def test_load_without_is_first_start_defaults_to_true(tmp_path: Path, settings_data: dict[str, Any]):
    """Если в файле нет флага первого запуска, считается, что запуск первый."""
    # Подготовка
    manager = SettingsManager()
    del settings_data["is_first_start"]

    # Действие
    manager.load(_write_json(tmp_path, settings_data))

    # Проверка
    assert manager.settings.is_first_start is True


# Подготовка
@pytest.mark.parametrize("file_name", ["", "   "])
def test_load_empty_file_name_other_cwd_reads_settings_from_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_name: str
):
    """Пустое имя файла означает settings.json в корне проекта, а не в текущем каталоге."""
    # Подготовка
    root_file = Common.find_project_root() / "settings.json"
    expected_name = json.loads(root_file.read_text(encoding="utf-8"))["organization"]["name"]
    monkeypatch.chdir(tmp_path)
    manager = SettingsManager()

    # Действие
    manager.load(file_name)

    # Проверка
    assert manager.settings.organization.name == expected_name


def test_load_empty_file_name_ignores_settings_in_current_directory(
    tmp_path: Path, settings_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
):
    """Файл settings.json в текущем каталоге не подменяет файл из корня проекта."""
    # Подготовка
    settings_data["organization"]["name"] = "Подмена"
    _write_json(tmp_path, settings_data)
    monkeypatch.chdir(tmp_path)
    manager = SettingsManager()

    # Действие
    manager.load()

    # Проверка
    assert manager.settings.organization.name != "Подмена"


def test_load_relative_file_name_resolved_from_current_directory(
    tmp_path: Path, settings_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
):
    """Явно переданный относительный путь отсчитывается от текущего каталога."""
    # Подготовка
    _write_json(tmp_path, settings_data, "custom.json")
    monkeypatch.chdir(tmp_path)
    manager = SettingsManager()

    # Действие
    manager.load("custom.json")

    # Проверка
    assert manager.settings.organization.name == "Ромашка"


def test_load_second_file_replaces_settings(tmp_path: Path, settings_data: dict[str, Any]):
    """Повторная загрузка другого файла заменяет настройки."""
    # Подготовка
    manager = SettingsManager()
    manager.load(_write_json(tmp_path, settings_data, "first.json"))
    settings_data["boss_name"] = "Сидоров Пётр Петрович"

    # Действие
    manager.load(_write_json(tmp_path, settings_data, "second.json"))

    # Проверка
    assert manager.settings.boss_name == "Сидоров Пётр Петрович"


# ---------------------------------------------------------------------------
# settings: доступ до и после загрузки
# ---------------------------------------------------------------------------


def test_settings_before_load_raises_operation_exception():
    """До загрузки обращение к настройкам бросает OperationException."""
    # Подготовка
    manager = SettingsManager()

    # Действие и проверка
    with pytest.raises(OperationException):
        _ = manager.settings


def test_settings_after_failed_reload_raises_operation_exception(tmp_path: Path, settings_data: dict[str, Any]):
    """После неудачной повторной загрузки старые настройки недоступны."""
    # Подготовка
    manager = SettingsManager()
    manager.load(_write_json(tmp_path, settings_data))

    # Действие
    with pytest.raises(OperationException):
        manager.load(str(tmp_path / "missing.json"))

    # Проверка
    with pytest.raises(OperationException):
        _ = manager.settings


# ---------------------------------------------------------------------------
# load: чтение файла
# ---------------------------------------------------------------------------


def test_load_missing_file_raises_operation_exception_with_file_name(tmp_path: Path):
    """Если файла нет, бросается OperationException с именем файла в тексте."""
    # Подготовка
    manager = SettingsManager()
    path = tmp_path / "missing.json"

    # Действие и проверка
    with pytest.raises(OperationException) as exc_info:
        manager.load(str(path))
    assert "missing.json" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)
    assert manager.is_loaded is False


def test_load_invalid_json_raises_operation_exception(tmp_path: Path):
    """Файл с некорректным JSON бросает OperationException."""
    # Подготовка
    manager = SettingsManager()
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(str(path))
    assert manager.is_loaded is False


def test_load_not_utf8_file_raises_operation_exception(tmp_path: Path):
    """Файл не в UTF-8 бросает OperationException, а не UnicodeDecodeError."""
    # Подготовка
    manager = SettingsManager()
    path = tmp_path / "cp1251.json"
    path.write_bytes('{"name": "Ромашка"}'.encode("cp1251"))

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(str(path))


# Подготовка
@pytest.mark.parametrize("content", [[], "text", 42, None])
def test_load_json_root_is_not_object_raises_operation_exception(tmp_path: Path, content: object):
    """Если корень JSON не объект, бросается OperationException."""
    # Подготовка
    manager = SettingsManager()
    path = _write_json(tmp_path, content)

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(path)
    assert manager.is_loaded is False


# ---------------------------------------------------------------------------
# load: преобразование
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize("key", ["organization", "boss_name", "account_name"])
def test_load_missing_top_level_key_raises_operation_exception_with_key_name(
    tmp_path: Path, settings_data: dict[str, Any], key: str
):
    """Отсутствие обязательного поля верхнего уровня бросает OperationException с его именем."""
    # Подготовка
    manager = SettingsManager()
    del settings_data[key]

    # Действие и проверка
    with pytest.raises(OperationException) as exc_info:
        manager.load(_write_json(tmp_path, settings_data))
    assert key in str(exc_info.value)
    assert manager.is_loaded is False


# Подготовка
@pytest.mark.parametrize("key", ["name", "inn", "bic", "account", "ownership_form"])
def test_load_missing_organization_key_raises_operation_exception_with_key_name(
    tmp_path: Path, settings_data: dict[str, Any], key: str
):
    """Отсутствие обязательного поля организации бросает OperationException с его именем."""
    # Подготовка
    manager = SettingsManager()
    del settings_data["organization"][key]

    # Действие и проверка
    with pytest.raises(OperationException) as exc_info:
        manager.load(_write_json(tmp_path, settings_data))
    assert key in str(exc_info.value)


# Подготовка
@pytest.mark.parametrize("organization", ["Ромашка", 42, [], None])
def test_load_organization_is_not_object_raises_operation_exception(
    tmp_path: Path, settings_data: dict[str, Any], organization: object
):
    """Если organization не объект, бросается OperationException."""
    # Подготовка
    manager = SettingsManager()
    settings_data["organization"] = organization

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(_write_json(tmp_path, settings_data))


def test_load_unknown_ownership_form_raises_operation_exception(tmp_path: Path, settings_data: dict[str, Any]):
    """Неизвестная форма собственности бросает OperationException."""
    # Подготовка
    manager = SettingsManager()
    settings_data["organization"]["ownership_form"] = "ЗАО-Мега"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(_write_json(tmp_path, settings_data))


def test_load_invalid_inn_raises_operation_exception_caused_by_arguments_exception(
    tmp_path: Path, settings_data: dict[str, Any]
):
    """Ошибка валидации модели оборачивается в OperationException с исходной причиной."""
    # Подготовка
    manager = SettingsManager()
    settings_data["organization"]["inn"] = "1234567890"

    # Действие и проверка
    with pytest.raises(OperationException) as exc_info:
        manager.load(_write_json(tmp_path, settings_data))
    assert isinstance(exc_info.value.__cause__, ArgumentsException)
    assert "inn" in str(exc_info.value)


# Подготовка
@pytest.mark.parametrize("key", ["boss_name", "account_name"])
def test_load_invalid_person_name_raises_operation_exception(tmp_path: Path, settings_data: dict[str, Any], key: str):
    """Нестроковое имя директора или бухгалтера бросает OperationException.

    Остальные случаи (пустое, из пробелов) проверены в test_common_validator и test_settings_model.
    """
    # Подготовка
    manager = SettingsManager()
    settings_data[key] = 42

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(_write_json(tmp_path, settings_data))


def test_load_is_first_start_not_bool_raises_operation_exception(tmp_path: Path, settings_data: dict[str, Any]):
    """Флаг первого запуска строкой вместо булева значения бросает OperationException."""
    # Подготовка
    manager = SettingsManager()
    settings_data["is_first_start"] = "true"

    # Действие и проверка
    with pytest.raises(OperationException):
        manager.load(_write_json(tmp_path, settings_data))

