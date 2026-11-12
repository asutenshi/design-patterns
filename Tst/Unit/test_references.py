import uuid

import pytest
from Src.Core.entity_type import EntityType
from Src.Core.exception import ArgumentsException
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


def _same_objects(left: list[object], right: list[object]) -> bool:
    """Сравнивает списки по тождеству элементов, с учётом порядка."""
    return len(left) == len(right) and all(a is b for a, b in zip(left, right, strict=True))


def test_references_group_and_warehouse_have_none():
    """Группа номенклатуры и склад ни на что не ссылаются."""
    # Действие и проверка
    assert NomenclatureGroupModel.create_meat().references() == []
    assert WarehouseModel.create_restaurant_warehouse().references() == []


def test_references_base_range_has_none():
    """Базовая единица ссылается сама на себя, но в ссылки себя не включает."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие и проверка
    assert gram.references() == []


def test_references_derived_range_returns_base():
    """Производная единица ссылается на свою базовую единицу."""
    # Подготовка
    kilogram = RangeModel.create_kilogram()

    # Действие
    refs = kilogram.references()

    # Проверка
    assert _same_objects(list(refs), [kilogram.base])


def test_references_nomenclature_returns_group_and_range():
    """Номенклатура ссылается на группу и единицу измерения."""
    # Подготовка
    group = NomenclatureGroupModel.create_meat()
    kilogram = RangeModel.create_kilogram()
    beef = NomenclatureModel.create_raw_material("Говядина", "Говядина охлаждённая", group, kilogram, 1000)

    # Действие
    refs = beef.references()

    # Проверка
    assert _same_objects(list(refs), [group, kilogram])


def test_references_raw_ingredient_returns_nomenclature():
    """Строка состава без основания ссылается только на свою номенклатуру."""
    # Подготовка
    beef = NomenclatureModel.create_raw_material(
        "Говядина", "Говядина охлаждённая", NomenclatureGroupModel.create_meat(), RangeModel.create_kilogram(), 1000
    )

    # Действие
    refs = IngredientModel(beef, 100).references()

    # Проверка
    assert _same_objects(list(refs), [beef])


def test_references_recipe_returns_result_and_every_ingredient_nomenclature(first_start_storage: StorageManager):
    """Карта ссылается на результат и на номенклатуру всех строк, включая основания составных строк."""
    # Подготовка
    borscht = next(recipe for recipe in first_start_storage.recipes if recipe.name == "Борщ с говядиной")

    # Действие
    refs = borscht.references()

    # Проверка
    assert refs[0] is borscht.result
    assert all(item.nomenclature in refs for item in borscht.items)
    # Основание полуфабриката раскрывается: сырьё из его карты тоже в ссылках
    nested = [nomenclature for item in borscht.items for nomenclature in item.references()]
    assert _same_objects(list(refs[1:]), list(nested))
    assert len(refs) > len(borscht.items) + 1


# Подготовка
@pytest.mark.parametrize("entity_type", list(EntityType), ids=lambda item: item.value)
def test_references_every_stored_entity_points_to_stored_entities(
    first_start_storage: StorageManager, entity_type: EntityType
):
    """Все ссылки сущностей из хранилища указывают на сущности, которые лежат в нём же (тот же объект)."""
    # Подготовка
    collections = {
        EntityType.NOMENCLATURE: first_start_storage.nomenclatures,
        EntityType.NOMENCLATURE_GROUP: first_start_storage.nomenclature_groups,
        EntityType.RANGE: first_start_storage.ranges,
        EntityType.WAREHOUSE: first_start_storage.warehouses,
        EntityType.RECIPE: first_start_storage.recipes,
    }
    stored = {
        id(entity): entity
        for collection in collections.values()
        for entity in collection
    }

    # Действие и проверка
    for entity in collections[entity_type]:
        assert all(id(ref) in stored for ref in entity.references())


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
    """Склад не используется другими сущностями, и для неизвестного кода тоже ничего не находится."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]

    # Действие и проверка
    assert first_start_storage.find_referrers(warehouse.id) == []
    assert first_start_storage.find_referrers(uuid.uuid4()) == []


# Подготовка
@pytest.mark.parametrize("target_id", ["not-a-uuid", None, 1])
def test_find_referrers_invalid_id_raises_arguments_exception(first_start_storage: StorageManager, target_id: object):
    """Код, не являющийся UUID, отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.find_referrers(target_id)  # pyright: ignore[reportArgumentType]
