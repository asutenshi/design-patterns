import uuid
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from Src.Core.entity_type import EntityType
from Src.Core.named_entity import NamedEntity
from Src.Core.response_format import ResponseFormat
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.storage_manager import StorageManager
from Src.main import app


@pytest.fixture
def client(first_start_storage: StorageManager) -> Iterator[TestClient]:
    """HTTP-клиент приложения с хранилищем, загруженным при первом запуске.

    Менеджеры загружены фикстурой заранее, поэтому lifespan приложения их не перезагружает.
    """
    with TestClient(app) as test_client:
        yield test_client


def _url(entity_type: EntityType, entity: NamedEntity | uuid.UUID | None = None) -> str:
    """Адрес коллекции сущностей типа или, если указана сущность или код, адрес одной сущности."""
    base = f"/api/entities/{entity_type.value}"
    if entity is None:
        return base
    entity_id = entity if isinstance(entity, uuid.UUID) else entity.id
    return f"{base}/{entity_id}"


def _by_name[T: NamedEntity](items: list[T], name: str) -> T:
    """Возвращает сущность из списка по наименованию."""
    return next(item for item in items if item.name == name)


def _ref(entity: NamedEntity) -> dict[str, str]:
    """Ссылка {"id": ...} на сущность хранилища."""
    return {"id": str(entity.id)}


def _nomenclature_data(storage: StorageManager, name: str = "Пастернак") -> dict[str, object]:
    """Данные новой номенклатуры со ссылками на группу «Овощи» и килограмм из хранилища."""
    return {
        "name": name,
        "full_name": f"{name} столовая",
        "group": _ref(_by_name(storage.nomenclature_groups, "Овощи")),
        "range": _ref(_by_name(storage.ranges, "килограмм")),
        "type": "сырьё",
        "grams_per_base_unit": 1,
    }


def _snapshot(storage: StorageManager) -> list[tuple[str, uuid.UUID]]:
    """Состав хранилища: наименование и код каждой сущности; по нему видно, что запрос ничего не изменил."""
    return [(entity.name, entity.id) for entity_type in EntityType for entity in storage.entities(entity_type)]


# ---------------------------------------------------------------------------
# Форматы отчётов
# ---------------------------------------------------------------------------


def test_get_report_formats_returns_all_response_formats(client: TestClient):
    """Список форматов — JSON-массив значений ResponseFormat в порядке объявления."""
    # Действие
    response = client.get("/api/get_report_formats")

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == [item.value for item in ResponseFormat]


# ---------------------------------------------------------------------------
# Чтение
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize("entity_type", list(EntityType), ids=lambda item: item.value)
def test_get_entities_returns_whole_collection_in_storage_format(
    client: TestClient, first_start_storage: StorageManager, entity_type: EntityType
):
    """Список сущностей типа совпадает с коллекцией хранилища в формате выгрузки ConverterFactory."""
    # Подготовка
    expected = [ConverterFactory().convert(entity) for entity in first_start_storage.entities(entity_type)]

    # Действие
    response = client.get(_url(entity_type))

    # Проверка
    assert response.status_code == 200
    assert expected
    assert response.json() == expected


def test_get_entity_returns_entity_in_storage_format(client: TestClient, first_start_storage: StorageManager):
    """Сущность по коду отдаётся в формате выгрузки: со своим кодом и вложенными группой и единицей."""
    # Подготовка
    beet = _by_name(first_start_storage.nomenclatures, "Свёкла")

    # Действие
    response = client.get(_url(EntityType.NOMENCLATURE, beet))

    # Проверка
    assert response.status_code == 200
    assert response.json() == ConverterFactory().convert(beet)
    assert response.json()["group"]["name"] == "Овощи"


def test_get_entity_id_of_other_type_returns_not_found(client: TestClient, first_start_storage: StorageManager):
    """Код склада не находит группу номенклатуры: поиск идёт только среди сущностей указанного типа."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]

    # Действие
    response = client.get(_url(EntityType.NOMENCLATURE_GROUP, warehouse))

    # Проверка
    assert response.status_code == 404
    assert str(warehouse.id) in response.json()["detail"]


# ---------------------------------------------------------------------------
# Создание
# ---------------------------------------------------------------------------


def test_create_entity_warehouse_returns_created_and_it_is_readable(
    client: TestClient, first_start_storage: StorageManager
):
    """POST создаёт склад: ответ 201 с кодом, склад есть в хранилище и читается по коду."""
    # Действие
    response = client.post(_url(EntityType.WAREHOUSE), json={"name": "Склад №3"})

    # Проверка
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Склад №3"
    entity_id = uuid.UUID(created["id"])
    assert first_start_storage.find(EntityType.WAREHOUSE, entity_id) is not None
    assert client.get(_url(EntityType.WAREHOUSE, entity_id)).json() == created


def test_create_entity_nomenclature_links_to_stored_entities(client: TestClient, first_start_storage: StorageManager):
    """Номенклатура со ссылками {"id": ...} ссылается на те же объекты группы и единицы, что лежат в хранилище."""
    # Подготовка
    data = _nomenclature_data(first_start_storage)

    # Действие
    response = client.post(_url(EntityType.NOMENCLATURE), json=data)

    # Проверка
    assert response.status_code == 201
    created = first_start_storage.find(EntityType.NOMENCLATURE, uuid.UUID(response.json()["id"]))
    assert created is not None
    assert created in first_start_storage.nomenclatures
    assert _by_name(first_start_storage.nomenclatures, "Пастернак").group is _by_name(
        first_start_storage.nomenclature_groups, "Овощи"
    )


def test_create_entity_with_given_id_uses_it(client: TestClient):
    """Код из тела запроса становится кодом новой сущности."""
    # Подготовка
    entity_id = uuid.uuid4()

    # Действие
    response = client.post(_url(EntityType.NOMENCLATURE_GROUP), json={"id": str(entity_id), "name": "Специи"})

    # Проверка
    assert response.status_code == 201
    assert response.json()["id"] == str(entity_id)


# Подготовка
@pytest.mark.parametrize(
    ("entity_type", "data"),
    [
        (EntityType.WAREHOUSE, {}),
        (EntityType.WAREHOUSE, {"name": "   "}),
        (EntityType.WAREHOUSE, {"name": "Склад", "model_type": "Src.Models.range_model.RangeModel"}),
        (EntityType.NOMENCLATURE, {"name": "Позиция", "group": {"id": str(uuid.uuid4())}}),
        (EntityType.RANGE, {"name": "центнер", "factor": -1, "base": None}),
    ],
    ids=["no_name", "blank_name", "wrong_model_type", "unknown_reference", "invalid_factor"],
)
def test_create_entity_invalid_data_returns_bad_request_and_keeps_storage(
    client: TestClient, first_start_storage: StorageManager, entity_type: EntityType, data: dict[str, object]
):
    """Некорректные данные отвергаются ответом 400 с пояснением, хранилище не меняется."""
    # Подготовка
    before = _snapshot(first_start_storage)

    # Действие
    response = client.post(_url(entity_type), json=data)

    # Проверка
    assert response.status_code == 400
    assert response.json()["detail"]
    assert _snapshot(first_start_storage) == before


def test_create_entity_duplicate_name_returns_bad_request(client: TestClient, first_start_storage: StorageManager):
    """Наименование, которое уже есть среди складов (без учёта регистра), занять нельзя."""
    # Подготовка
    existing = first_start_storage.warehouses[0]
    before = _snapshot(first_start_storage)

    # Действие
    response = client.post(_url(EntityType.WAREHOUSE), json={"name": existing.name.upper()})

    # Проверка
    assert response.status_code == 400
    assert _snapshot(first_start_storage) == before


def test_create_entity_body_not_object_returns_unprocessable_entity(client: TestClient):
    """Тело запроса не JSON-объект: FastAPI отвергает его с ответом 422 до хранилища."""
    # Действие
    response = client.post(_url(EntityType.WAREHOUSE), json=["Склад"])

    # Проверка
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Изменение: PUT
# ---------------------------------------------------------------------------


def test_put_entity_renames_referenced_group_in_place(client: TestClient, first_start_storage: StorageManager):
    """Группу, на которую ссылается номенклатура, можно переименовать: номенклатура видит новое наименование."""
    # Подготовка
    group = _by_name(first_start_storage.nomenclature_groups, "Овощи")
    beet = _by_name(first_start_storage.nomenclatures, "Свёкла")

    # Действие
    response = client.put(_url(EntityType.NOMENCLATURE_GROUP, group), json={"name": "Овощи и зелень"})

    # Проверка
    assert response.status_code == 200
    assert response.json()["id"] == str(group.id)
    assert client.get(_url(EntityType.NOMENCLATURE, beet)).json()["group"]["name"] == "Овощи и зелень"


def test_put_entity_missing_required_field_returns_bad_request_and_keeps_entity(
    client: TestClient, first_start_storage: StorageManager
):
    """PUT заменяет все поля: без обязательных полей номенклатура не собирается, старая не меняется."""
    # Подготовка
    beet = _by_name(first_start_storage.nomenclatures, "Свёкла")
    before = ConverterFactory().convert(beet)

    # Действие
    response = client.put(_url(EntityType.NOMENCLATURE, beet), json={"name": "Свёкла"})

    # Проверка
    assert response.status_code == 400
    assert ConverterFactory().convert(beet) == before


def test_put_entity_new_id_of_unreferenced_entity_changes_code(client: TestClient, first_start_storage: StorageManager):
    """Код склада, на который никто не ссылается, можно сменить: старый адрес больше не находит склад."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]
    old_id, new_id = warehouse.id, uuid.uuid4()

    # Действие
    response = client.put(_url(EntityType.WAREHOUSE, old_id), json={"id": str(new_id), "name": warehouse.name})

    # Проверка
    assert response.status_code == 200
    assert client.get(_url(EntityType.WAREHOUSE, old_id)).status_code == 404
    assert client.get(_url(EntityType.WAREHOUSE, new_id)).status_code == 200


def test_put_entity_new_id_of_referenced_entity_returns_conflict(
    client: TestClient, first_start_storage: StorageManager
):
    """Сменить код группы, на которую ссылается номенклатура, нельзя: 409 со списком ссылающихся, группа прежняя."""
    # Подготовка
    group = _by_name(first_start_storage.nomenclature_groups, "Овощи")
    before = _snapshot(first_start_storage)

    # Действие
    response = client.put(
        _url(EntityType.NOMENCLATURE_GROUP, group), json={"id": str(uuid.uuid4()), "name": "Другое"}
    )

    # Проверка
    assert response.status_code == 409
    body = response.json()
    assert str(group.id) in body["detail"]
    assert any("Свёкла" in referrer for referrer in cast(list[str], body["referrers"]))
    assert _snapshot(first_start_storage) == before


def test_put_entity_unknown_id_returns_not_found(client: TestClient):
    """Изменить сущность, которой нет, нельзя: 404."""
    # Действие
    response = client.put(_url(EntityType.WAREHOUSE, uuid.uuid4()), json={"name": "Склад"})

    # Проверка
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Изменение: PATCH
# ---------------------------------------------------------------------------


def test_patch_entity_changes_only_given_fields(client: TestClient, first_start_storage: StorageManager):
    """PATCH меняет указанное поле, остальные поля номенклатуры остаются прежними."""
    # Подготовка
    beet = _by_name(first_start_storage.nomenclatures, "Свёкла")
    before = cast(dict[str, object], ConverterFactory().convert(beet))

    # Действие
    response = client.patch(_url(EntityType.NOMENCLATURE, beet), json={"full_name": "Свёкла столовая отборная"})

    # Проверка
    assert response.status_code == 200
    assert response.json() == {**before, "full_name": "Свёкла столовая отборная"}


def test_patch_entity_reference_switches_to_other_stored_entity(
    client: TestClient, first_start_storage: StorageManager
):
    """Ссылку номенклатуры на группу можно перенаправить на другую группу хранилища."""
    # Подготовка
    beet = _by_name(first_start_storage.nomenclatures, "Свёкла")
    meat = _by_name(first_start_storage.nomenclature_groups, "Мясные продукты")

    # Действие
    response = client.patch(_url(EntityType.NOMENCLATURE, beet), json={"group": _ref(meat)})

    # Проверка
    assert response.status_code == 200
    assert beet.group is meat


def test_patch_entity_new_id_of_recipe_result_returns_conflict(client: TestClient, first_start_storage: StorageManager):
    """Номенклатура-результат карты связана с картой: сменить ей код нельзя."""
    # Подготовка
    recipe = _by_name(first_start_storage.recipes, "Борщ с говядиной")
    result_id = recipe.result.id

    # Действие
    response = client.patch(_url(EntityType.NOMENCLATURE, result_id), json={"id": str(uuid.uuid4())})

    # Проверка
    assert response.status_code == 409
    assert recipe.result.id == result_id


def test_patch_entity_unknown_id_returns_not_found(client: TestClient):
    """Изменить сущность, которой нет, нельзя: 404."""
    # Действие
    response = client.patch(_url(EntityType.RANGE, uuid.uuid4()), json={"name": "г"})

    # Проверка
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Удаление
# ---------------------------------------------------------------------------


def test_delete_entity_unreferenced_returns_no_content_and_removes_it(
    client: TestClient, first_start_storage: StorageManager
):
    """Склад, на который никто не ссылается, удаляется: 204 без тела, затем GET отвечает 404."""
    # Подготовка
    warehouse = first_start_storage.warehouses[0]

    # Действие
    response = client.delete(_url(EntityType.WAREHOUSE, warehouse))

    # Проверка
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(_url(EntityType.WAREHOUSE, warehouse)).status_code == 404


# Подготовка
@pytest.mark.parametrize(
    ("entity_type", "name"),
    [
        (EntityType.NOMENCLATURE_GROUP, "Овощи"),
        (EntityType.RANGE, "грамм"),
        (EntityType.NOMENCLATURE, "Свёкла"),
    ],
    ids=["group_used_by_nomenclature", "base_range_used_by_kilogram", "raw_material_used_by_recipe"],
)
def test_delete_entity_referenced_returns_conflict_and_keeps_it(
    client: TestClient, first_start_storage: StorageManager, entity_type: EntityType, name: str
):
    """Сущность, на которую ссылаются другие сущности, не удаляется: 409 со списком ссылающихся."""
    # Подготовка
    entity = _by_name(first_start_storage.entities(entity_type), name)
    before = _snapshot(first_start_storage)

    # Действие
    response = client.delete(_url(entity_type, entity))

    # Проверка
    assert response.status_code == 409
    assert response.json()["referrers"]
    assert _snapshot(first_start_storage) == before


def test_delete_entity_recipe_then_its_result_succeeds(client: TestClient, first_start_storage: StorageManager):
    """Результат карты нельзя удалить, пока есть карта; после удаления карты результат удаляется."""
    # Подготовка
    recipe = _by_name(first_start_storage.recipes, "Борщ с говядиной")
    result = recipe.result

    # Действие
    blocked = client.delete(_url(EntityType.NOMENCLATURE, result))
    recipe_deleted = client.delete(_url(EntityType.RECIPE, recipe))
    result_deleted = client.delete(_url(EntityType.NOMENCLATURE, result))

    # Проверка
    assert (blocked.status_code, recipe_deleted.status_code, result_deleted.status_code) == (409, 204, 204)


def test_delete_entity_unknown_id_returns_not_found(client: TestClient):
    """Удалить сущность, которой нет, нельзя: 404."""
    # Действие
    response = client.delete(_url(EntityType.WAREHOUSE, uuid.uuid4()))

    # Проверка
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Общие проверки маршрутов и полный цикл
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/entities/employee"),
        ("GET", "/api/entities/warehouse/not-a-uuid"),
        ("PUT", "/api/entities/warehouse/not-a-uuid"),
        ("PATCH", "/api/entities/employee/00000000-0000-0000-0000-000000000000"),
        ("DELETE", "/api/entities/warehouse/not-a-uuid"),
    ],
    ids=["unknown_type", "get_invalid_id", "put_invalid_id", "patch_unknown_type", "delete_invalid_id"],
)
def test_entity_routes_invalid_path_returns_unprocessable_entity(client: TestClient, method: str, path: str):
    """Тип не из EntityType и код не в виде UUID FastAPI отвергает с ответом 422."""
    # Действие
    response = client.request(method, path, json={"name": "Склад"})

    # Проверка
    assert response.status_code == 422


def test_entity_routes_full_cycle_create_read_update_delete(client: TestClient):
    """Полный цикл через API: группа создаётся, на неё ссылается новая номенклатура, и пока ссылка есть,
    группу нельзя удалить; после удаления номенклатуры группа удаляется."""
    # Подготовка
    kilogram = next(item for item in client.get(_url(EntityType.RANGE)).json() if item["name"] == "килограмм")

    # Действие
    group = client.post(_url(EntityType.NOMENCLATURE_GROUP), json={"name": "Зелень"}).json()
    item = client.post(
        _url(EntityType.NOMENCLATURE),
        json={
            "name": "Кинза",
            "full_name": "Кинза свежая",
            "group": {"id": group["id"]},
            "range": {"id": kilogram["id"]},
            "type": "сырьё",
            "grams_per_base_unit": 1,
        },
    ).json()
    renamed = client.patch(f"{_url(EntityType.NOMENCLATURE_GROUP)}/{group['id']}", json={"name": "Свежая зелень"})
    read = client.get(f"{_url(EntityType.NOMENCLATURE)}/{item['id']}").json()
    blocked = client.delete(f"{_url(EntityType.NOMENCLATURE_GROUP)}/{group['id']}")
    item_deleted = client.delete(f"{_url(EntityType.NOMENCLATURE)}/{item['id']}")
    group_deleted = client.delete(f"{_url(EntityType.NOMENCLATURE_GROUP)}/{group['id']}")

    # Проверка
    assert renamed.status_code == 200
    assert read["group"] == {**group, "name": "Свежая зелень"}
    assert blocked.status_code == 409
    assert (item_deleted.status_code, group_deleted.status_code) == (204, 204)
    assert client.get(f"{_url(EntityType.NOMENCLATURE_GROUP)}/{group['id']}").status_code == 404
