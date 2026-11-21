from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from Src.Core.entity_type import EntityType
from Src.Logics.storage_manager import StorageManager
from Src.main import app


@pytest.fixture
def client(first_start_storage: StorageManager) -> Iterator[TestClient]:
    """HTTP-клиент приложения с хранилищем, загруженным при первом запуске."""
    with TestClient(app) as test_client:
        yield test_client


def _condition(field_name: str, filter_type: str, value: str) -> dict[str, str]:
    """Одно условие фильтра в формате тела запроса."""
    return {"field_name": field_name, "filter_type": filter_type, "value": value}


def _names(response_json: object) -> list[str]:
    """Наименования сущностей из ответа фильтра."""
    assert isinstance(response_json, list)
    return [item["name"] for item in response_json]  # pyright: ignore[reportUnknownVariableType]


# Подготовка
@pytest.mark.parametrize(
    ("entity_type", "condition", "expected"),
    [
        (EntityType.NOMENCLATURE, _condition("name", "EQUALS", "Говядина"), ["Говядина"]),
        (
            EntityType.NOMENCLATURE,
            _condition("name", "LIKE", "Говядина"),
            ["Говядина", "Говядина (мякоть)", "Говядина отварная"],
        ),
        (EntityType.NOMENCLATURE_GROUP, _condition("name", "LIKE", "продукты"), ["Мясные продукты", "Молочные продукты"]),
        (EntityType.RANGE, _condition("base.name", "EQUALS", "литр"), []),
        (EntityType.RANGE, _condition("base.name", "EQUALS", "миллилитр"), ["миллилитр", "литр"]),
        (EntityType.RECIPE, _condition("items.nomenclature.name", "EQUALS", "Картофель"), ["Борщ с говядиной"]),
    ],
    ids=["nomenclature_equals", "nomenclature_like", "group_like", "range_nested_empty", "range_nested", "recipe_items"],
)
def test_filter_entities_returns_matching_entities(
    client: TestClient, entity_type: EntityType, condition: dict[str, str], expected: list[str]
):
    """Фильтр отбирает сущности типа из маршрута по условию, в том числе по вложенным моделям и коллекциям."""
    # Действие
    response = client.post(f"/api/filter/{entity_type.value}", json={"filters": [condition]})

    # Проверка
    assert response.status_code == 200
    assert _names(response.json()) == expected


def test_filter_entities_by_id_returns_one_entity(client: TestClient, first_start_storage: StorageManager):
    """Фильтр по уникальному коду находит ровно одну сущность и отдаёт её в формате выгрузки."""
    # Подготовка
    salt = next(item for item in first_start_storage.nomenclatures if item.name == "Соль")

    # Действие
    response = client.post(
        f"/api/filter/{EntityType.NOMENCLATURE.value}", json={"filters": [_condition("id", "EQUALS", str(salt.id))]}
    )

    # Проверка
    assert response.status_code == 200
    assert [(item["id"], item["name"]) for item in response.json()] == [(str(salt.id), "Соль")]


def test_filter_entities_several_conditions_all_must_match(client: TestClient):
    """Условия работают как логическое И: остаются только сущности, прошедшие все условия."""
    # Подготовка
    body = {"filters": [_condition("name", "LIKE", "Говядина"), _condition("full_name", "LIKE", "охлаждённая")]}

    # Действие
    response = client.post(f"/api/filter/{EntityType.NOMENCLATURE.value}", json=body)

    # Проверка
    assert response.status_code == 200
    assert _names(response.json()) == ["Говядина", "Говядина (мякоть)"]


def test_filter_entities_empty_filters_returns_all(client: TestClient, first_start_storage: StorageManager):
    """Пустой список условий возвращает все сущности типа."""
    # Действие
    response = client.post(f"/api/filter/{EntityType.WAREHOUSE.value}", json={"filters": []})

    # Проверка
    assert response.status_code == 200
    assert _names(response.json()) == [item.name for item in first_start_storage.warehouses]


# Подготовка
@pytest.mark.parametrize(
    "body",
    [
        {"filters": [_condition("_range._factor", "EQUALS", "1000")]},
        {"filters": [_condition("unknown", "EQUALS", "1")]},
        {"filters": [_condition("name", "STARTS_WITH", "Го")]},
        {"filters": [{"field_name": "name", "filter_type": "EQUALS"}]},
        {},
    ],
    ids=["private_field", "unknown_field", "unknown_filter_type", "missing_value", "missing_filters"],
)
def test_filter_entities_invalid_body_returns_400(client: TestClient, body: dict[str, object]):
    """Недоступное поле, неизвестный способ сравнения или неполное условие — ошибка клиента 400."""
    # Действие
    response = client.post(f"/api/filter/{EntityType.NOMENCLATURE.value}", json=body)

    # Проверка
    assert response.status_code == 400


def test_filter_entities_unknown_entity_type_returns_422(client: TestClient):
    """Неизвестный тип сущности в маршруте отклоняет FastAPI при разборе пути."""
    # Действие
    response = client.post("/api/filter/unknown", json={"filters": []})

    # Проверка
    assert response.status_code == 422
