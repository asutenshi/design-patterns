import json
from collections.abc import Callable
from pathlib import Path

import pytest
from Src.Core.exception import OperationException
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager

# Начальные данные, которые создаются при первом запуске
EXPECTED_RANGES = ["грамм", "килограмм", "миллилитр", "литр", "штука"]
EXPECTED_GROUPS = ["Мясные продукты", "Молочные продукты", "Упаковка"]
EXPECTED_NOMENCLATURES = ["Говядина", "Молоко", "Стакан"]
EXPECTED_WAREHOUSES = ["Склад ресторана", "Склад производственного цеха"]


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


# ---------------------------------------------------------------------------
# До загрузки и ошибки
# ---------------------------------------------------------------------------


def test_properties_before_load_are_empty():
    """До load() все коллекции пусты."""
    # Подготовка
    storage = StorageManager()

    # Действие
    collections = [storage.ranges, storage.nomenclature_groups, storage.nomenclatures, storage.warehouses]

    # Проверка
    assert collections == [[], [], [], []]


def test_load_settings_not_loaded_raises_operation_exception():
    """Без загруженных настроек load() бросает OperationException."""
    # Подготовка
    storage = StorageManager()

    # Действие и проверка
    with pytest.raises(OperationException):
        storage.load()
    assert storage.is_loaded is False
    assert storage.ranges == []


# ---------------------------------------------------------------------------
# Первый запуск
# ---------------------------------------------------------------------------


def test_load_first_start_creates_ranges(first_start_storage: StorageManager):
    """При первом запуске создаются единицы измерения."""
    # Действие
    names = [item.name for item in first_start_storage.ranges]

    # Проверка
    assert names == EXPECTED_RANGES


def test_load_first_start_creates_nomenclature_groups(first_start_storage: StorageManager):
    """При первом запуске создаются группы номенклатуры."""
    # Действие
    names = [item.name for item in first_start_storage.nomenclature_groups]

    # Проверка
    assert names == EXPECTED_GROUPS


def test_load_first_start_creates_nomenclatures(first_start_storage: StorageManager):
    """При первом запуске создаётся номенклатура."""
    # Действие
    names = [item.name for item in first_start_storage.nomenclatures]

    # Проверка
    assert names == EXPECTED_NOMENCLATURES


def test_load_first_start_creates_warehouses(first_start_storage: StorageManager):
    """При первом запуске создаются склады."""
    # Действие
    names = [item.name for item in first_start_storage.warehouses]

    # Проверка
    assert names == EXPECTED_WAREHOUSES


def test_load_first_start_derived_range_references_stored_base(first_start_storage: StorageManager):
    """Производная единица ссылается на ту же базовую, что лежит в коллекции."""
    # Подготовка
    ranges = {item.name: item for item in first_start_storage.ranges}

    # Действие и проверка
    assert ranges["килограмм"].base is ranges["грамм"]
    assert ranges["литр"].base is ranges["миллилитр"]
    assert ranges["килограмм"].factor == 1000
    assert ranges["литр"].factor == 1000


def test_load_first_start_nomenclature_references_stored_range_and_group(first_start_storage: StorageManager):
    """Номенклатура хранит те же объекты единицы и группы, что лежат в коллекциях, а не копии."""
    # Подготовка
    ranges = first_start_storage.ranges
    groups = first_start_storage.nomenclature_groups

    # Действие и проверка
    for nomenclature in first_start_storage.nomenclatures:
        assert any(nomenclature.range is item for item in ranges)
        assert any(nomenclature.group is item for item in groups)


# Подготовка
@pytest.mark.parametrize(
    ("nomenclature_name", "group_name", "range_name", "base_range_name"),
    [
        ("Говядина", "Мясные продукты", "килограмм", "грамм"),
        ("Молоко", "Молочные продукты", "литр", "миллилитр"),
        ("Стакан", "Упаковка", "штука", "штука"),
    ],
)
def test_load_first_start_nomenclature_uses_its_own_stored_group_and_range(
    first_start_storage: StorageManager,
    nomenclature_name: str,
    group_name: str,
    range_name: str,
    base_range_name: str,
):
    """Номенклатура ссылается на свою группу и свою единицу из коллекций (те же объекты, не копии).

    Для говядины это группа «Мясные продукты» и килограмм, а база килограмма — тот же грамм,
    что лежит в коллекции единиц.
    """
    # Подготовка
    nomenclatures = {item.name: item for item in first_start_storage.nomenclatures}
    groups = {item.name: item for item in first_start_storage.nomenclature_groups}
    ranges = {item.name: item for item in first_start_storage.ranges}

    # Действие
    nomenclature = nomenclatures[nomenclature_name]

    # Проверка
    assert nomenclature.group is groups[group_name]
    assert nomenclature.range is ranges[range_name]
    assert nomenclature.range.base is ranges[base_range_name]


# Подготовка
@pytest.mark.parametrize(
    "collection", ["ranges", "nomenclature_groups", "nomenclatures", "warehouses"]
)
def test_load_first_start_elements_are_unique_by_id_and_name(first_start_storage: StorageManager, collection: str):
    """В каждой коллекции нет повторяющихся идентификаторов и наименований."""
    # Подготовка
    items = getattr(first_start_storage, collection)

    # Действие
    ids = [item.id for item in items]
    names = [item.name.casefold() for item in items]

    # Проверка
    assert len(items) > 0
    assert len(set(ids)) == len(ids)
    assert len(set(names)) == len(names)


def test_load_first_start_ids_are_unique_across_all_collections(first_start_storage: StorageManager):
    """Идентификаторы не повторяются и между коллекциями."""
    # Подготовка
    items = [
        *first_start_storage.ranges,
        *first_start_storage.nomenclature_groups,
        *first_start_storage.nomenclatures,
        *first_start_storage.warehouses,
    ]

    # Действие
    ids = [item.id for item in items]

    # Проверка
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------------
# Не первый запуск и повторная загрузка
# ---------------------------------------------------------------------------


def test_load_not_first_start_collections_stay_empty(load_settings: Callable[[bool], None]):
    """Если запуск не первый, начальные данные не создаются."""
    # Подготовка
    load_settings(False)
    storage = StorageManager()

    # Действие
    storage.load()

    # Проверка
    assert storage.ranges == []
    assert storage.nomenclature_groups == []
    assert storage.nomenclatures == []
    assert storage.warehouses == []


def test_load_repeated_first_start_does_not_duplicate_elements(first_start_storage: StorageManager):
    """Повторная загрузка пересоздаёт данные, а не дописывает их к прежним."""
    # Действие
    first_start_storage.load()

    # Проверка
    assert len(first_start_storage.ranges) == len(EXPECTED_RANGES)
    assert len(first_start_storage.nomenclature_groups) == len(EXPECTED_GROUPS)
    assert len(first_start_storage.nomenclatures) == len(EXPECTED_NOMENCLATURES)
    assert len(first_start_storage.warehouses) == len(EXPECTED_WAREHOUSES)


def test_load_repeated_after_first_start_flag_off_clears_collections(
    first_start_storage: StorageManager, load_settings: Callable[[bool], None]
):
    """Если после первого запуска флаг сброшен, повторная загрузка очищает коллекции."""
    # Подготовка
    load_settings(False)

    # Действие
    first_start_storage.load()

    # Проверка
    assert first_start_storage.ranges == []
    assert first_start_storage.warehouses == []


def test_load_settings_reload_fails_raises_and_is_loaded_becomes_false(
    first_start_storage: StorageManager, tmp_path: Path
):
    """Если настройки не удалось перечитать, повторная загрузка хранилища падает и сбрасывает is_loaded."""
    # Подготовка
    broken = tmp_path / "broken.json"
    broken.write_text("{}", encoding="utf-8")
    with pytest.raises(OperationException):
        SettingsManager().load(str(broken))

    # Действие и проверка
    with pytest.raises(OperationException):
        first_start_storage.load()
    assert first_start_storage.is_loaded is False


# ---------------------------------------------------------------------------
# Защита от изменения снаружи
# ---------------------------------------------------------------------------


def test_properties_returned_list_modification_does_not_change_storage(first_start_storage: StorageManager):
    """Изменение возвращённого списка не меняет коллекцию в хранилище."""
    # Подготовка
    ranges = first_start_storage.ranges

    # Действие
    ranges.clear()

    # Проверка
    assert len(first_start_storage.ranges) == len(EXPECTED_RANGES)