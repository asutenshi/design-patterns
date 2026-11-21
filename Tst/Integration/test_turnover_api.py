from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from Src.Logics.storage_manager import StorageManager
from Src.main import app

# Строка ОСВ в удобном для сравнения виде: номенклатура, склад, единица, начало, приход, расход, конец
type Row = tuple[str, str, str, float, float, float, float]

_URL = "/api/turnover"
RESTAURANT = "Склад ресторана"
WORKSHOP = "Склад производственного цеха"


@pytest.fixture
def client(first_start_storage: StorageManager) -> Iterator[TestClient]:
    """HTTP-клиент приложения с хранилищем и журналом, загруженными при первом запуске."""
    with TestClient(app) as test_client:
        yield test_client


def _rows(report: dict[str, object]) -> list[Row]:
    """Описывает строки ОСВ из ответа: наименования вложенных моделей и четыре колонки."""
    rows = cast(list[dict[str, dict[str, str] | float]], report["rows"])
    return [
        (
            cast(dict[str, str], row["nomenclature"])["name"],
            cast(dict[str, str], row["warehouse"])["name"],
            cast(dict[str, str], row["range"])["name"],
            cast(float, row["opening"]),
            cast(float, row["income"]),
            cast(float, row["outcome"]),
            cast(float, row["closing"]),
        )
        for row in rows
    ]


def test_get_turnover_october_returns_period_and_rows(client: TestClient):
    """ОСВ за октябрь по всему журналу: период из запроса и строка на каждую пару «номенклатура + склад»."""
    # Действие
    response = client.post(_URL, json={"start": "2026-10-01", "end": "2026-10-31", "filters": []})

    # Проверка
    assert response.status_code == 200
    report = cast(dict[str, object], response.json())
    assert (report["start"], report["end"]) == ("2026-10-01", "2026-10-31")
    assert _rows(report) == [
        ("Говядина", RESTAURANT, "грамм", 3000, 3000, 4000, 2000),
        ("Молоко", WORKSHOP, "миллилитр", 0, 5000, 1500, 3500),
        ("Картофель", RESTAURANT, "грамм", 0, 10000, 0, 10000),
        ("Говядина", WORKSHOP, "грамм", 0, 2000, 0, 2000),
    ]


def test_get_turnover_filter_by_warehouse_name(client: TestClient):
    """Условие по вложенному полю записи журнала оставляет в ОСВ только один склад."""
    # Подготовка
    body = {
        "start": "2026-10-01",
        "end": "2026-10-31",
        "filters": [{"field_name": "warehouse.name", "filter_type": "EQUALS", "value": RESTAURANT}],
    }

    # Действие
    response = client.post(_URL, json=body)

    # Проверка
    assert response.status_code == 200
    assert _rows(cast(dict[str, object], response.json())) == [
        ("Говядина", RESTAURANT, "грамм", 3000, 3000, 4000, 2000),
        ("Картофель", RESTAURANT, "грамм", 0, 10000, 0, 10000),
    ]


def test_get_turnover_without_start_begins_at_first_record(client: TestClient):
    """Без начала периода ОСВ строится с даты первой отобранной записи, поэтому остаток на начало нулевой."""
    # Подготовка
    body = {
        "end": "2026-10-31",
        "filters": [{"field_name": "nomenclature.name", "filter_type": "EQUALS", "value": "Молоко"}],
    }

    # Действие
    response = client.post(_URL, json=body)

    # Проверка
    assert response.status_code == 200
    report = cast(dict[str, object], response.json())
    assert report["start"] == "2026-10-03"
    assert _rows(report) == [("Молоко", WORKSHOP, "миллилитр", 0, 5000, 1500, 3500)]


# Подготовка
@pytest.mark.parametrize(
    "body",
    [
        {"start": "01.10.2026", "filters": []},
        {"start": "2026-10-31", "end": "2026-10-01", "filters": []},
        {"filters": [{"field_name": "_quantity", "filter_type": "EQUALS", "value": "1"}]},
        {"start": "2026-10-01"},
    ],
    ids=["bad_date_format", "start_after_end", "private_field", "missing_filters"],
)
def test_get_turnover_invalid_body_returns_400(client: TestClient, body: dict[str, object]):
    """Неверная дата, перевёрнутый период, недоступное поле или отсутствие условий — ошибка клиента 400."""
    # Действие
    response = client.post(_URL, json=body)

    # Проверка
    assert response.status_code == 400


def test_get_turnover_nomenclature_range_changed_returns_500(client: TestClient, first_start_storage: StorageManager):
    """Единицу молока сменили на килограмм после записей в литрах: ОСВ не строится, сервер отвечает 500."""
    # Подготовка
    milk = next(item for item in first_start_storage.nomenclatures if item.name == "Молоко")
    milk.range = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    response = client.post(_URL, json={"start": "2026-10-01", "end": "2026-10-31", "filters": []})

    # Проверка
    assert response.status_code == 500
    assert "Молоко" in response.json()["detail"]
