import uuid
from collections.abc import Callable

import pytest
from Src.Core.entity_type import EntityType
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.reference_scanner import ReferenceScanner
from Src.Logics.storage_manager import StorageManager
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


def _same_objects(left: list[object], right: list[object]) -> bool:
    """Сравнивает списки по тождеству элементов, с учётом порядка."""
    return len(left) == len(right) and all(a is b for a, b in zip(left, right, strict=True))


# Подготовка
@pytest.mark.parametrize("entity_type", list(EntityType), ids=lambda item: item.value)
def test_scan_every_stored_entity_points_to_stored_entities(
    first_start_storage: StorageManager, entity_type: EntityType
):
    """Все ссылки сущностей из хранилища указывают на сущности, которые лежат в нём же (тот же объект)."""
    # Подготовка
    scanner = ReferenceScanner()
    stored = {id(entity): entity for entity in first_start_storage.all_entities()}

    # Действие и проверка
    for entity in first_start_storage.entities(entity_type):
        assert all(id(ref) in stored for ref in scanner.scan(entity))


def test_scan_every_stored_transaction_points_to_stored_entities(first_start_storage: StorageManager):
    """Все ссылки записей журнала указывают на сущности, которые лежат в хранилище (тот же объект)."""
    # Подготовка
    scanner = ReferenceScanner()
    stored = {id(entity): entity for entity in first_start_storage.all_entities()}

    # Действие и проверка
    for transaction in first_start_storage.transactions:
        assert all(id(ref) in stored for ref in scanner.scan(transaction))


def test_find_referrers_group_returns_its_nomenclatures(first_start_storage: StorageManager):
    """На группу ссылается ровно та номенклатура, у которой она указана; другие сущности не попадают."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    expected = [item for item in first_start_storage.nomenclatures if item.group is group]

    # Действие
    referrers = first_start_storage.find_referrers(group.id)

    # Проверка
    assert len(expected) > 0
    assert _same_objects(list(referrers), list(expected))


def test_find_referrers_base_range_returns_derived_ranges_but_not_itself(first_start_storage: StorageManager):
    """На грамм ссылаются килограмм и номенклатура в граммах, а сам грамм (ссылка на себя) в результат не входит."""
    # Подготовка
    gram = next(item for item in first_start_storage.ranges if item.name == "грамм")

    # Действие
    referrers = first_start_storage.find_referrers(gram.id)

    # Проверка
    assert all(referrer is not gram for referrer in referrers)
    assert any(referrer.name == "килограмм" for referrer in referrers)


def test_find_referrers_recipe_result_returns_its_recipe(first_start_storage: StorageManager):
    """На номенклатуру-результат ссылается её карта."""
    # Подготовка
    recipe = next(item for item in first_start_storage.recipes if item.name == "Борщ с говядиной")

    # Действие
    referrers = first_start_storage.find_referrers(recipe.result.id)

    # Проверка
    assert any(referrer is recipe for referrer in referrers)


def test_find_referrers_raw_material_inside_semi_finished_base_returns_recipe_once(
    first_start_storage: StorageManager,
):
    """Сырьё, которое входит в основание строки, связывает с картой борща, и карта возвращается один раз."""
    # Подготовка
    borscht = next(item for item in first_start_storage.recipes if item.name == "Борщ с говядиной")
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    assert all(item.nomenclature is not beet for item in borscht.items)

    # Действие
    referrers = first_start_storage.find_referrers(beet.id)

    # Проверка
    assert sum(referrer is borscht for referrer in referrers) == 1


def test_find_referrers_unreferenced_entity_returns_empty(first_start_storage: StorageManager):
    """Новый склад не используется другими сущностями, и для неизвестного кода тоже ничего не находится."""
    # Подготовка
    warehouse = WarehouseModel("Склад без операций")
    first_start_storage.add(EntityType.WAREHOUSE, warehouse)

    # Действие и проверка
    assert first_start_storage.find_referrers(warehouse.id) == []
    assert first_start_storage.find_referrers(uuid.uuid4()) == []


def _new_nomenclature(storage: StorageManager, name: str) -> NomenclatureModel:
    """Создаёт номенклатуру на группе «Овощи» и килограмме хранилища, в хранилище не добавляет."""
    group = next(item for item in storage.nomenclature_groups if item.name == "Овощи")
    kilogram = next(item for item in storage.ranges if item.name == "килограмм")
    return NomenclatureModel(name, name, group, kilogram, NomenclatureType.RAW_MATERIAL, 1000)


def _copy_with_range(nomenclature: NomenclatureModel, range_model: RangeModel) -> NomenclatureModel:
    """Возвращает номенклатуру с теми же полями и кодом, но другой единицей измерения."""
    state = NomenclatureModel(
        nomenclature.name,
        nomenclature.full_name,
        nomenclature.group,
        range_model,
        nomenclature.type,
        nomenclature.grams_per_base_unit,
    )
    state.id = nomenclature.id
    return state


def test_find_referrers_after_add_returns_new_entity(first_start_storage: StorageManager):
    """Добавленная через add() номенклатура сразу находится среди ссылающихся на свою группу и единицу."""
    # Подготовка
    nomenclature = _new_nomenclature(first_start_storage, "Редис")

    # Действие
    first_start_storage.add(EntityType.NOMENCLATURE, nomenclature)

    # Проверка
    assert any(item is nomenclature for item in first_start_storage.find_referrers(nomenclature.group.id))
    assert any(item is nomenclature for item in first_start_storage.find_referrers(nomenclature.range.id))


def test_find_referrers_after_remove_does_not_return_entity(first_start_storage: StorageManager):
    """Убранная номенклатура больше не числится среди ссылающихся."""
    # Подготовка
    nomenclature = _new_nomenclature(first_start_storage, "Редис")
    first_start_storage.add(EntityType.NOMENCLATURE, nomenclature)

    # Действие
    first_start_storage.remove(EntityType.NOMENCLATURE, nomenclature)

    # Проверка
    assert all(item is not nomenclature for item in first_start_storage.find_referrers(nomenclature.range.id))


def test_find_referrers_after_replace_follows_new_references(first_start_storage: StorageManager):
    """Сменили единицу номенклатуры с килограмма на литр: ссылка переезжает в индексе на литр."""
    # Подготовка
    nomenclature = _new_nomenclature(first_start_storage, "Редис")
    first_start_storage.add(EntityType.NOMENCLATURE, nomenclature)
    kilogram = nomenclature.range
    liter = next(item for item in first_start_storage.ranges if item.name == "литр")

    # Действие
    first_start_storage.replace(EntityType.NOMENCLATURE, nomenclature, _copy_with_range(nomenclature, liter))

    # Проверка
    assert all(item is not nomenclature for item in first_start_storage.find_referrers(kilogram.id))
    assert any(item is nomenclature for item in first_start_storage.find_referrers(liter.id))


def test_find_referrers_after_replace_with_new_id_keeps_and_removes_entity(first_start_storage: StorageManager):
    """Смена кода у ссылающейся сущности не теряет её в индексе: она находится и потом убирается."""
    # Подготовка
    nomenclature = _new_nomenclature(first_start_storage, "Редис")
    first_start_storage.add(EntityType.NOMENCLATURE, nomenclature)
    state = _copy_with_range(nomenclature, nomenclature.range)
    state.id = uuid.uuid4()

    # Действие
    first_start_storage.replace(EntityType.NOMENCLATURE, nomenclature, state)
    found = any(item is nomenclature for item in first_start_storage.find_referrers(nomenclature.range.id))
    first_start_storage.remove(EntityType.NOMENCLATURE, nomenclature)

    # Проверка
    assert found
    assert all(item is not nomenclature for item in first_start_storage.find_referrers(nomenclature.range.id))


def test_find_referrers_result_change_does_not_affect_storage(first_start_storage: StorageManager):
    """Результат — копия: очистка списка снаружи не стирает ссылки в хранилище."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    expected = first_start_storage.find_referrers(group.id)

    # Действие
    first_start_storage.find_referrers(group.id).clear()

    # Проверка
    assert len(expected) > 0
    assert _same_objects(list(first_start_storage.find_referrers(group.id)), list(expected))


def test_find_referrers_after_reload_without_data_returns_empty(
    first_start_storage: StorageManager, load_settings: Callable[..., None]
):
    """Повторная загрузка без начальных данных очищает индекс вместе с коллекциями."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    load_settings(False)

    # Действие
    first_start_storage.load()

    # Проверка
    assert first_start_storage.find_referrers(group.id) == []


# Подготовка
@pytest.mark.parametrize("target_id", ["not-a-uuid", None, 1])
def test_find_referrers_invalid_id_raises_arguments_exception(first_start_storage: StorageManager, target_id: object):
    """Код, не являющийся UUID, отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.find_referrers(target_id)  # pyright: ignore[reportArgumentType]
