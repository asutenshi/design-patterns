from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from Src.Logics.storage_manager import StorageManager
from Src.Logics.txt_report import TxtReport
from Src.main import app


@pytest.fixture
def client(first_start_storage: StorageManager) -> Iterator[TestClient]:
    """HTTP-клиент приложения с хранилищем, загруженным при первом запуске.

    Менеджеры загружены фикстурой заранее, поэтому lifespan приложения их не перезагружает
    и не трогает settings.json в корне проекта.
    """
    with TestClient(app) as test_client:
        yield test_client


def test_get_report_existing_recipe_returns_txt_report(client: TestClient, first_start_storage: StorageManager):
    """Для существующей карты возвращается текстовый отчёт, совпадающий с TxtReport по той же карте."""
    # Подготовка
    recipe = first_start_storage.find_recipe_by_name("Борщ с говядиной")
    assert recipe is not None

    # Действие
    response = client.get("/api/get_report", params={"recipe_name": "Борщ с говядиной", "response_format": "txt"})

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.text == TxtReport().build(recipe).text


# Подготовка
@pytest.mark.parametrize("params", [{"recipe_name": "Борщ с говядиной"}, {"recipe_name": "  борщ С ГОВЯДИНОЙ "}])
def test_get_report_format_omitted_or_name_in_other_case_returns_report(client: TestClient, params: dict[str, str]):
    """Без response_format берётся формат из настроек (здесь TXT), наименование ищется без учёта регистра и пробелов."""
    # Действие
    response = client.get("/api/get_report", params=params)

    # Проверка
    assert response.status_code == 200
    assert "name: Борщ с говядиной" in response.text.split("\n")


def test_get_report_unknown_recipe_returns_not_found(client: TestClient):
    """Для неизвестной карты возвращается 404 с наименованием в тексте ошибки."""
    # Подготовка
    params = {"recipe_name": "Несуществующая карта"}

    # Действие
    response = client.get("/api/get_report", params=params)

    # Проверка
    assert response.status_code == 404
    assert "Несуществующая карта" in response.json()["detail"]


# Подготовка
@pytest.mark.parametrize(
    "params", [{}, {"recipe_name": "Борщ с говядиной", "response_format": "pdf"}], ids=["no_name", "unknown_format"]
)
def test_get_report_invalid_params_returns_unprocessable_entity(client: TestClient, params: dict[str, str]):
    """Без обязательного recipe_name или с форматом не из ResponseFormat FastAPI отвечает 422."""
    # Действие
    response = client.get("/api/get_report", params=params)

    # Проверка
    assert response.status_code == 422


def test_lifespan_not_loaded_managers_loads_them(load_settings: Callable[[bool], None]):
    """При старте приложения lifespan загружает хранилище, если его не загрузили заранее."""
    # Подготовка
    load_settings(True)

    # Действие
    with TestClient(app):
        storage = StorageManager()

    # Проверка
    assert storage.is_loaded
    assert storage.recipes


def test_get_report_format_omitted_csv_settings_returns_csv_file(load_settings: Callable[..., None]):
    """Без response_format отчёт строится в формате из настроек: CSV отдаётся файлом на скачивание."""
    # Подготовка
    load_settings(True, "csv")
    storage = StorageManager()
    storage.load()

    # Действие
    with TestClient(app) as client:
        response = client.get("/api/get_report", params={"recipe_name": "Борщ с говядиной"})

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].startswith('attachment; filename="recipe-')
