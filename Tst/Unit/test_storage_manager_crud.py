import uuid
from typing import cast

import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.entity_type import EntityType
from Src.Core.exception import ArgumentsException, ReferencedEntityException
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.storage_manager import StorageManager
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


def _ref(entity: BaseEntity) -> dict[str, str]:
    """Ссылка {"id": ...} на сущность хранилища."""
    return {"id": str(entity.id)}


def _nomenclature_data(storage: StorageManager, name: str = "Тестовая позиция") -> dict[str, object]:
    """Данные новой номенклатуры, которая ссылается на группу «Овощи» и килограмм из хранилища."""
    group = next(item for item in storage.nomenclature_groups if item.name == "Овощи")
    kilogram = next(item for item in storage.ranges if item.name == "килограмм")
    return {
        "name": name,
        "full_name": f"{name}, полное наименование",
        "group": _ref(group),
        "range": _ref(kilogram),
        "type": "сырьё",
        "grams_per_base_unit": 1,
    }


def _snapshot(storage: StorageManager) -> list[tuple[str, uuid.UUID]]:
    """Состав хранилища: наименование и код каждой сущности; по нему видно, что операция ничего не изменила."""
    return [
        (entity.name, entity.id)
        for entity_type in EntityType
        for entity in getattr(storage, _COLLECTION[entity_type])
    ]


_COLLECTION = {
    EntityType.NOMENCLATURE: "nomenclatures",
    EntityType.NOMENCLATURE_GROUP: "nomenclature_groups",
    EntityType.RANGE: "ranges",
    EntityType.WAREHOUSE: "warehouses",
    EntityType.RECIPE: "recipes",
}


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_nomenclature_links_to_stored_group_and_range_and_is_found(first_start_storage: StorageManager):
    """Созданная номенклатура ссылается на те же объекты группы и единицы, лежит в хранилище и находится по коду."""
    # Подготовка
    data = _nomenclature_data(first_start_storage)

    # Действие
    created = cast(NomenclatureModel, first_start_storage.create(EntityType.NOMENCLATURE, data))

    # Проверка
    assert created.group is next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    assert created.range is next(item for item in first_start_storage.ranges if item.name == "килограмм")
    assert first_start_storage.find(EntityType.NOMENCLATURE, created.id) is created
    assert created in first_start_storage.nomenclatures


@pytest.mark.parametrize("entity_type", [EntityType.WAREHOUSE, EntityType.NOMENCLATURE_GROUP])
def test_create_simple_entity_is_added_to_collection(first_start_storage: StorageManager, entity_type: EntityType):
    """Склад и группа создаются по одному наименованию."""
    # Действие
    created = first_start_storage.create(entity_type, {"name": "Новая запись"})

    # Проверка
    assert first_start_storage.find(entity_type, created.id) is created


def test_create_with_given_id_uses_it(first_start_storage: StorageManager):
    """Код из данных становится кодом сущности."""
    # Подготовка
    new_id = uuid.uuid4()

    # Действие
    created = first_start_storage.create(EntityType.WAREHOUSE, {"id": str(new_id), "name": "Склад с кодом"})

    # Проверка
    assert created.id == new_id


def test_create_accepts_matching_model_type(first_start_storage: StorageManager):
    """Совпадающий model_type допускается."""
    # Действие
    created = first_start_storage.create(
        EntityType.WAREHOUSE, {"model_type": "Src.Models.warehouse_model.WarehouseModel", "name": "Склад"}
    )

    # Проверка
    assert first_start_storage.find(EntityType.WAREHOUSE, created.id) is created


# Подготовка
@pytest.mark.parametrize(
    ("entity_type", "data"),
    [
        (EntityType.WAREHOUSE, {"model_type": "Src.Models.range_model.RangeModel", "name": "Склад"}),
        (EntityType.WAREHOUSE, {}),
        (EntityType.WAREHOUSE, {"name": "   "}),
        (EntityType.WAREHOUSE, "не словарь"),
        (EntityType.NOMENCLATURE, {"name": "Позиция", "group": {"id": str(uuid.uuid4())}}),
    ],
    ids=["wrong_model_type", "no_name", "blank_name", "not_dict", "unknown_reference"],
)
def test_create_invalid_data_raises_arguments_exception_and_keeps_storage(
    first_start_storage: StorageManager, entity_type: EntityType, data: object
):
    """Некорректные данные отвергаются ArgumentsException, хранилище не меняется."""
    # Подготовка
    before = _snapshot(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.create(entity_type, data)  # pyright: ignore[reportArgumentType]
    assert _snapshot(first_start_storage) == before


def test_create_duplicate_name_raises_arguments_exception(first_start_storage: StorageManager):
    """Наименование, которое уже есть в коллекции, отвергается (без учёта регистра)."""
    # Подготовка
    existing = first_start_storage.warehouses[0]
    before = _snapshot(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.create(EntityType.WAREHOUSE, {"name": existing.name.upper()})
    assert _snapshot(first_start_storage) == before


@pytest.mark.parametrize("other_type", [EntityType.WAREHOUSE, EntityType.NOMENCLATURE_GROUP])
def test_create_taken_id_raises_arguments_exception(first_start_storage: StorageManager, other_type: EntityType):
    """Код, который уже есть у любой сущности хранилища, занять нельзя."""
    # Подготовка
    taken = first_start_storage.warehouses[0]
    before = _snapshot(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.create(other_type, {"id": str(taken.id), "name": "Другая запись"})
    assert _snapshot(first_start_storage) == before


def test_create_invalid_entity_type_raises_arguments_exception(first_start_storage: StorageManager):
    """Тип не из EntityType отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.create("warehouse", {"name": "Склад"})  # pyright: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# put
# ---------------------------------------------------------------------------


def test_put_replaces_fields_in_place_and_referrers_see_it(first_start_storage: StorageManager):
    """Группа, на которую ссылаются, переименовывается на месте: номенклатура видит новое наименование."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")

    # Действие
    result = first_start_storage.put(EntityType.NOMENCLATURE_GROUP, group.id, {"name": "Овощи и зелень"})

    # Проверка
    assert result is group
    assert group.id == beet.group.id
    assert beet.group is group
    assert beet.group.name == "Овощи и зелень"


def test_put_without_id_keeps_id(first_start_storage: StorageManager):
    """Если в данных нет id, код сущности остаётся прежним."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]
    old_id = warehouse.id

    # Действие
    _ = first_start_storage.put(EntityType.WAREHOUSE, old_id, {"name": "Переименованный склад"})

    # Проверка
    assert warehouse.id == old_id
    assert first_start_storage.find(EntityType.WAREHOUSE, old_id) is warehouse


def test_put_renamed_entity_is_reachable_by_new_name_and_old_name_is_free(first_start_storage: StorageManager):
    """После переименования старое наименование освобождается, а новое занято."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]
    old_name = warehouse.name

    # Действие
    _ = first_start_storage.put(EntityType.WAREHOUSE, warehouse.id, {"name": "Новое имя"})

    # Проверка
    _ = first_start_storage.create(EntityType.WAREHOUSE, {"name": old_name})
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.create(EntityType.WAREHOUSE, {"name": "новое ИМЯ"})


def test_put_same_name_keeps_collection_order(first_start_storage: StorageManager):
    """Правка без смены наименования не меняет порядок элементов."""
    # Подготовка
    names_before = [item.name for item in first_start_storage.nomenclatures]
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    data = _nomenclature_data(first_start_storage, "Свёкла")

    # Действие
    _ = first_start_storage.put(EntityType.NOMENCLATURE, beet.id, data)

    # Проверка
    assert [item.name for item in first_start_storage.nomenclatures] == names_before


def test_put_unreferenced_entity_changes_id(first_start_storage: StorageManager):
    """Код сущности, на которую никто не ссылается, можно заменить."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]
    old_id = warehouse.id
    new_id = uuid.uuid4()

    # Действие
    _ = first_start_storage.put(EntityType.WAREHOUSE, old_id, {"id": str(new_id), "name": warehouse.name})

    # Проверка
    assert warehouse.id == new_id
    assert first_start_storage.find(EntityType.WAREHOUSE, old_id) is None
    assert first_start_storage.find(EntityType.WAREHOUSE, new_id) is warehouse


def test_put_referenced_entity_new_id_raises_referenced_entity_exception(first_start_storage: StorageManager):
    """Код группы, на которую ссылается номенклатура, менять нельзя: исключение называет ссылающихся."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    old_id, old_name = group.id, group.name
    before = _snapshot(first_start_storage)

    # Действие
    with pytest.raises(ReferencedEntityException) as exc_info:
        _ = first_start_storage.put(EntityType.NOMENCLATURE_GROUP, old_id, {"id": str(uuid.uuid4()), "name": "Другое"})

    # Проверка
    assert exc_info.value.target_id == old_id
    assert any("Свёкла" in referrer for referrer in exc_info.value.referrers)
    assert (group.id, group.name) == (old_id, old_name)
    assert _snapshot(first_start_storage) == before


def test_put_taken_id_raises_arguments_exception(first_start_storage: StorageManager):
    """Новый код, занятый другой сущностью, отвергается, и та сущность не затрагивается."""
    # Подготовка
    first, second = first_start_storage.warehouses
    before = _snapshot(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.put(EntityType.WAREHOUSE, first.id, {"id": str(second.id), "name": first.name})
    assert _snapshot(first_start_storage) == before


def test_put_duplicate_name_raises_arguments_exception_and_keeps_entity(first_start_storage: StorageManager):
    """Наименование другой сущности занять нельзя, сущность не меняется."""
    # Подготовка
    first, second = first_start_storage.warehouses
    first_name = first.name
    before = _snapshot(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.put(EntityType.WAREHOUSE, first.id, {"name": second.name})
    assert first.name == first_name
    assert _snapshot(first_start_storage) == before


def test_put_missing_required_field_raises_arguments_exception_and_keeps_entity(first_start_storage: StorageManager):
    """Put заменяет все поля: без обязательного поля номенклатура не собирается, а старая не меняется."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    old_full_name = beet.full_name

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.put(EntityType.NOMENCLATURE, beet.id, {"name": "Свёкла"})
    assert beet.full_name == old_full_name


def test_put_unknown_entity_raises_arguments_exception(first_start_storage: StorageManager):
    """Сущности с таким кодом нет."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.put(EntityType.WAREHOUSE, uuid.uuid4(), {"name": "Склад"})


def test_put_recipe_name_keeps_result_key(first_start_storage: StorageManager):
    """Карту можно переименовать: она остаётся единственной картой своего результата."""
    # Подготовка
    recipe = next(item for item in first_start_storage.recipes if item.name == "Борщ с говядиной")
    data = cast(dict[str, object], ConverterFactory().convert(recipe))
    data["name"] = "Борщ украинский"

    # Действие
    result = cast(RecipeModel, first_start_storage.put(EntityType.RECIPE, recipe.id, data))

    # Проверка
    assert result is recipe
    assert recipe.name == "Борщ украинский"
    assert first_start_storage.find_recipe(recipe.result) is recipe
    assert first_start_storage.find_recipe_by_name("борщ украинский") is recipe


# ---------------------------------------------------------------------------
# patch
# ---------------------------------------------------------------------------


def test_patch_changes_only_given_fields(first_start_storage: StorageManager):
    """Патч меняет указанные поля, остальные остаются, ссылки сохраняют тождество объектов."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    group, unit, full_name = beet.group, beet.range, beet.full_name

    # Действие
    result = first_start_storage.patch(EntityType.NOMENCLATURE, beet.id, {"grams_per_base_unit": 7})

    # Проверка
    assert result is beet
    assert beet.grams_per_base_unit == 7
    assert (beet.group, beet.range, beet.full_name) == (group, unit, full_name)
    assert beet.group is group
    assert beet.range is unit


def test_patch_reference_field_switches_to_other_stored_entity(first_start_storage: StorageManager):
    """Ссылочное поле можно перенаправить на другую сущность хранилища."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    meat = next(item for item in first_start_storage.nomenclature_groups if item.name == "Мясные продукты")

    # Действие
    _ = first_start_storage.patch(EntityType.NOMENCLATURE, beet.id, {"group": _ref(meat)})

    # Проверка
    assert beet.group is meat


def test_patch_unknown_reference_raises_arguments_exception_and_keeps_entity(first_start_storage: StorageManager):
    """Ссылка на несуществующую группу отвергается."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")
    group = beet.group

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.patch(EntityType.NOMENCLATURE, beet.id, {"group": {"id": str(uuid.uuid4())}})
    assert beet.group is group


def test_patch_derived_range_keeps_base(first_start_storage: StorageManager):
    """Правка производной единицы сохраняет ссылку на ту же базовую единицу."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")
    base = kilogram.base

    # Действие
    _ = first_start_storage.patch(EntityType.RANGE, kilogram.id, {"name": "кг"})

    # Проверка
    assert kilogram.name == "кг"
    assert kilogram.base is base


def test_patch_base_range_keeps_self_reference(first_start_storage: StorageManager):
    """Базовая единица после правки по-прежнему ссылается на себя, а не на временный объект."""
    # Подготовка
    gram = next(item for item in first_start_storage.ranges if item.name == "грамм")

    # Действие
    result = cast(RangeModel, first_start_storage.patch(EntityType.RANGE, gram.id, {"name": "г"}))

    # Проверка
    assert result is gram
    assert gram.base is gram
    assert gram.is_base


def test_patch_referenced_entity_id_raises_referenced_entity_exception(first_start_storage: StorageManager):
    """Сменить код номенклатуры, которая нужна карте, нельзя."""
    # Подготовка
    recipe = first_start_storage.recipes[0]
    result_id = recipe.result.id

    # Действие
    with pytest.raises(ReferencedEntityException):
        _ = first_start_storage.patch(EntityType.NOMENCLATURE, result_id, {"id": str(uuid.uuid4())})

    # Проверка
    assert recipe.result.id == result_id


def test_patch_id_to_same_value_is_allowed_for_referenced_entity(first_start_storage: StorageManager):
    """Код, равный текущему, не считается сменой кода, и сущность, на которую ссылаются, правится."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")

    # Действие
    _ = first_start_storage.patch(EntityType.NOMENCLATURE_GROUP, group.id, {"id": str(group.id), "name": "Овощи 2"})

    # Проверка
    assert group.name == "Овощи 2"


def test_patch_unknown_entity_raises_arguments_exception(first_start_storage: StorageManager):
    """Сущности с таким кодом нет."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = first_start_storage.patch(EntityType.WAREHOUSE, uuid.uuid4(), {"name": "Склад"})


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_unreferenced_entity_removes_it(first_start_storage: StorageManager):
    """Склад, на который никто не ссылается, удаляется и больше не находится; наименование освобождается."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]

    # Действие
    first_start_storage.delete(EntityType.WAREHOUSE, warehouse.id)

    # Проверка
    assert first_start_storage.find(EntityType.WAREHOUSE, warehouse.id) is None
    assert warehouse not in first_start_storage.warehouses
    _ = first_start_storage.create(EntityType.WAREHOUSE, {"name": warehouse.name})


def test_delete_referenced_entity_raises_and_keeps_it(first_start_storage: StorageManager):
    """Группа, на которую ссылается номенклатура, не удаляется; в исключении есть ссылающиеся."""
    # Подготовка
    group = next(item for item in first_start_storage.nomenclature_groups if item.name == "Овощи")
    before = _snapshot(first_start_storage)

    # Действие
    with pytest.raises(ReferencedEntityException) as exc_info:
        first_start_storage.delete(EntityType.NOMENCLATURE_GROUP, group.id)

    # Проверка
    assert exc_info.value.target_id == group.id
    assert len(exc_info.value.referrers) > 0
    assert _snapshot(first_start_storage) == before


def test_delete_recipe_result_is_blocked_but_recipe_itself_can_be_deleted(first_start_storage: StorageManager):
    """Номенклатуру-результат удалить нельзя, пока есть её карта; саму карту можно, после этого результат свободен."""
    # Подготовка
    recipe = next(item for item in first_start_storage.recipes if item.name == "Борщ с говядиной")
    result = recipe.result

    # Действие и проверка
    with pytest.raises(ReferencedEntityException):
        first_start_storage.delete(EntityType.NOMENCLATURE, result.id)
    first_start_storage.delete(EntityType.RECIPE, recipe.id)
    first_start_storage.delete(EntityType.NOMENCLATURE, result.id)
    assert first_start_storage.find(EntityType.NOMENCLATURE, result.id) is None


def test_delete_base_range_with_derived_is_blocked(first_start_storage: StorageManager):
    """Грамм нельзя удалить, пока на него ссылается килограмм; сама самоссылка базовой единицы не мешает."""
    # Подготовка
    gram = next(item for item in first_start_storage.ranges if item.name == "грамм")

    # Действие и проверка
    with pytest.raises(ReferencedEntityException):
        first_start_storage.delete(EntityType.RANGE, gram.id)


def test_delete_after_referrer_removed_succeeds(first_start_storage: StorageManager):
    """Созданная группа удаляется, пока на неё не сослались; после создания номенклатуры с ней — нельзя."""
    # Подготовка
    group = first_start_storage.create(EntityType.NOMENCLATURE_GROUP, {"name": "Временная"})
    data = _nomenclature_data(first_start_storage)
    data["group"] = _ref(group)
    item = first_start_storage.create(EntityType.NOMENCLATURE, data)

    # Действие и проверка
    with pytest.raises(ReferencedEntityException):
        first_start_storage.delete(EntityType.NOMENCLATURE_GROUP, group.id)
    first_start_storage.delete(EntityType.NOMENCLATURE, item.id)
    first_start_storage.delete(EntityType.NOMENCLATURE_GROUP, group.id)
    assert first_start_storage.find(EntityType.NOMENCLATURE_GROUP, group.id) is None


def test_delete_unknown_entity_raises_arguments_exception(first_start_storage: StorageManager):
    """Сущности с таким кодом нет."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        first_start_storage.delete(EntityType.WAREHOUSE, uuid.uuid4())


def test_delete_other_type_id_raises_arguments_exception(first_start_storage: StorageManager):
    """Код склада не находит сущность в коллекции групп."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        first_start_storage.delete(EntityType.NOMENCLATURE_GROUP, warehouse.id)
