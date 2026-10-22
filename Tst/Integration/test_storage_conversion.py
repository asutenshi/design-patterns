import json
from typing import cast

from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.storage_manager import StorageManager


def test_convert_storage_returns_all_collections(first_start_storage: StorageManager):
    """Загруженное хранилище превращается в один вложенный словарь со всеми коллекциями."""
    # Действие
    result = ConverterFactory().convert(first_start_storage)

    # Проверка
    for field, items in [
        ("ranges", first_start_storage.ranges),
        ("nomenclature_groups", first_start_storage.nomenclature_groups),
        ("nomenclatures", first_start_storage.nomenclatures),
        ("warehouses", first_start_storage.warehouses),
        ("recipes", first_start_storage.recipes),
    ]:
        converted = cast(list[dict[str, object]], result[field])
        assert [item["id"] for item in converted] == [str(item.id) for item in items]


def test_convert_storage_composite_recipe_contains_nested_base(first_start_storage: StorageManager):
    """Составная карта из начальных данных записывается с вложенными основаниями полуфабрикатов."""
    # Подготовка
    borscht = next(recipe for recipe in first_start_storage.recipes if any(item.base for item in recipe.items))

    # Действие
    result = ConverterFactory().convert(borscht)

    # Проверка
    items = cast(list[dict[str, object]], result["items"])
    assert any(item["base"] for item in items)
    assert items == [ConverterFactory().convert(item) for item in borscht.items]


def test_convert_storage_result_is_serialized_by_json(first_start_storage: StorageManager):
    """Словарь всего хранилища записывается json.dumps и читается обратно без потерь."""
    # Подготовка
    result = ConverterFactory().convert(first_start_storage)

    # Действие
    restored: object = json.loads(json.dumps(result, ensure_ascii=False))

    # Проверка
    assert restored == result
