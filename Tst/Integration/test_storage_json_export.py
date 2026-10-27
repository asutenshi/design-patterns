import json
import os
import re
import uuid
from pathlib import Path
from typing import cast

import pytest
from Src.Core.named_entity import NamedEntity
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.storage_manager import StorageManager

# Коллекции хранилища в порядке выгрузки
_COLLECTIONS = ("ranges", "nomenclature_groups", "nomenclatures", "warehouses", "recipes")
# Пример выгрузки в репозитории: его видно без запуска кода, а тест следит, чтобы он не устарел
_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "Docs" / "Examples" / "storage_first_start.json"
# Переменная окружения, с которой тест перезаписывает пример свежей выгрузкой
_UPDATE_EXAMPLE_ENV = "UPDATE_EXAMPLES"
# Код UUID в тексте выгрузки
_UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _export(storage: StorageManager, path: Path) -> None:
    """Выгружает всё хранилище в JSON-файл так же, как это сделает клиент: словарь фабрики и json.dump."""
    data = ConverterFactory().convert(storage)
    _ = path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read(path: Path) -> dict[str, object]:
    """Читает выгруженный JSON-файл."""
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _label_ids(text: str) -> str:
    """Заменяет коды UUID метками по порядку первого появления.

    Коды новые при каждом запуске, а метки одинаковые: одна и та же сущность получает одну метку,
    поэтому связи между сущностями (ссылки на группу, единицу, номенклатуру) при сравнении сохраняются.
    """
    labels: dict[str, str] = {}

    def label(match: re.Match[str]) -> str:
        return labels.setdefault(match.group(0), f"id-{len(labels) + 1}")

    return _UUID_PATTERN.sub(label, text)


def _items(exported: dict[str, object], collection: str) -> list[dict[str, object]]:
    """Возвращает элементы коллекции из выгрузки."""
    return cast(list[dict[str, object]], exported[collection])


@pytest.fixture
def exported_path(first_start_storage: StorageManager, tmp_path: Path) -> Path:
    """Путь к JSON-файлу с выгрузкой хранилища, загруженного при первом запуске."""
    path = tmp_path / "storage.json"
    _export(first_start_storage, path)
    return path


def test_export_first_start_contains_all_collections(exported_path: Path):
    """Выгрузка содержит флаг загрузки и все пять коллекций хранилища, и ничего больше."""
    # Действие
    exported = _read(exported_path)

    # Проверка
    assert list(exported) == ["is_loaded", *_COLLECTIONS]
    assert exported["is_loaded"] is True


@pytest.mark.parametrize("collection", _COLLECTIONS)
def test_export_first_start_collection_keeps_ids_and_names_in_order(
    first_start_storage: StorageManager, exported_path: Path, collection: str
):
    """Каждая коллекция выгружается полностью: те же элементы, тот же порядок, код — строкой."""
    # Подготовка
    stored = cast(list[NamedEntity], getattr(first_start_storage, collection))
    exported = _items(_read(exported_path), collection)

    # Проверка
    assert stored
    assert [(item["id"], item["name"]) for item in exported] == [(str(item.id), item.name) for item in stored]


def test_export_first_start_ids_are_valid_uuid_and_unique(exported_path: Path):
    """Коды всех выгруженных элементов — корректные UUID, и ни один не повторяется между коллекциями."""
    # Подготовка
    exported = _read(exported_path)

    # Действие
    ids = [item["id"] for collection in _COLLECTIONS for item in _items(exported, collection)]

    # Проверка
    assert len(set(ids)) == len(ids)
    assert all(str(uuid.UUID(cast(str, item_id))) == item_id for item_id in ids)


def test_export_first_start_nomenclature_contains_nested_group_and_range(
    first_start_storage: StorageManager, exported_path: Path
):
    """Номенклатура выгружается с вложенными группой и единицей измерения, а тип — значением перечисления."""
    # Подготовка
    exported = _items(_read(exported_path), "nomenclatures")

    # Проверка
    for stored, item in zip(first_start_storage.nomenclatures, exported, strict=True):
        assert item["group"] == {"id": str(stored.group.id), "name": stored.group.name}
        assert cast(dict[str, object], item["range"])["id"] == str(stored.range.id)
        assert item["type"] == stored.type.value


def test_export_first_start_base_range_refers_to_itself_by_id(
    first_start_storage: StorageManager, exported_path: Path
):
    """Базовая единица замыкает цикл ссылкой {"id": ...}, а производная раскрывает свою базовую целиком."""
    # Подготовка
    exported = _items(_read(exported_path), "ranges")

    # Проверка
    for stored, item in zip(first_start_storage.ranges, exported, strict=True):
        if stored.is_base:
            assert item["base"] == {"id": str(stored.id)}
        else:
            base = cast(dict[str, object], item["base"])
            assert base["id"] == str(stored.base.id)
            assert base["name"] == stored.base.name


def test_export_first_start_recipes_refer_to_exported_nomenclatures(exported_path: Path):
    """Результат карты и каждая позиция состава — номенклатура из выгрузки: их коды есть среди номенклатур."""
    # Подготовка
    exported = _read(exported_path)
    nomenclature_ids = {item["id"] for item in _items(exported, "nomenclatures")}

    # Проверка
    for recipe in _items(exported, "recipes"):
        assert cast(dict[str, object], recipe["result"])["id"] in nomenclature_ids
        for row in cast(list[dict[str, object]], recipe["items"]):
            assert cast(dict[str, object], row["nomenclature"])["id"] in nomenclature_ids


def test_export_first_start_composite_recipe_contains_nested_base_rows(exported_path: Path):
    """Составная карта выгружается с основанием полуфабрикатов: у позиции вложен список строк состава."""
    # Подготовка
    recipes = _items(_read(exported_path), "recipes")

    # Действие
    composite = [
        row
        for recipe in recipes
        for row in cast(list[dict[str, object]], recipe["items"])
        if row["base"]
    ]

    # Проверка
    assert composite
    for row in composite:
        base = cast(list[dict[str, object]], row["base"])
        assert all("nomenclature" in base_row and "quantity" in base_row for base_row in base)


def test_export_first_start_keeps_cyrillic_as_is(exported_path: Path):
    """Файл записан в UTF-8 без экранирования: кириллица читается прямо в тексте."""
    # Действие
    text = exported_path.read_text(encoding="utf-8")

    # Проверка
    assert "Говядина" in text
    assert "\\u" not in text


def test_export_first_start_twice_gives_identical_files(first_start_storage: StorageManager, tmp_path: Path):
    """Повторная выгрузка того же хранилища даёт тот же файл: фабрика не копит состояние между вызовами."""
    # Подготовка
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    # Действие
    _export(first_start_storage, first)
    _export(first_start_storage, second)

    # Проверка
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_export_first_start_matches_example_file(exported_path: Path):
    """Пример выгрузки в Docs/Examples совпадает со свежей выгрузкой с точностью до кодов UUID.

    Если начальные данные или конвертеры изменились, тест падает. Пример обновляется так:
    ``UPDATE_EXAMPLES=1 uv run pytest Tst/Integration/test_storage_json_export.py``.
    """
    # Подготовка
    exported = exported_path.read_text(encoding="utf-8")
    if os.environ.get(_UPDATE_EXAMPLE_ENV):
        _EXAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ = _EXAMPLE_PATH.write_text(exported, encoding="utf-8")

    # Действие
    example = _EXAMPLE_PATH.read_text(encoding="utf-8")

    # Проверка
    assert _label_ids(example) == _label_ids(exported)
