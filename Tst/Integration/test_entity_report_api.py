import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from Src.Core.abstract_report import AbstractReport
from Src.Core.entity_type import EntityType
from Src.Core.named_entity import NamedEntity
from Src.Core.response_format import ResponseFormat
from Src.Logics.csv_report import CsvReport
from Src.Logics.markdown_report import MarkdownReport
from Src.Logics.storage_manager import StorageManager
from Src.Logics.txt_report import TxtReport
from Src.Logics.xml_report import XmlReport
from Src.main import app


@pytest.fixture
def client(first_start_storage: StorageManager) -> Iterator[TestClient]:
    """HTTP-клиент приложения с хранилищем, загруженным при первом запуске (формат по умолчанию — TXT).

    Менеджеры загружены фикстурой заранее, поэтому lifespan приложения их не перезагружает
    и не трогает settings.json в корне проекта.
    """
    with TestClient(app) as test_client:
        yield test_client


def _entity(storage: StorageManager, entity_type: EntityType) -> NamedEntity:
    """Возвращает сущность указанного типа из начальных данных."""
    entities: dict[EntityType, NamedEntity] = {
        EntityType.NOMENCLATURE: next(item for item in storage.nomenclatures if item.name == "Свёкла"),
        EntityType.RANGE: next(item for item in storage.ranges if item.name == "килограмм"),
        EntityType.RECIPE: next(item for item in storage.recipes if item.name == "Борщ с говядиной"),
    }
    return entities[entity_type]


# Подготовка
@pytest.mark.parametrize("entity_type", list(EntityType), ids=lambda item: item.value)
def test_get_entity_report_xml_returns_text_matching_report(
    client: TestClient, first_start_storage: StorageManager, entity_type: EntityType
):
    """Для каждого типа сущности XML-отчёт отдаётся текстом, совпадающим с XmlReport по той же сущности."""
    # Подготовка
    entity = _entity(first_start_storage, entity_type)

    # Действие
    response = client.get(f"/api/reports/xml/{entity_type.value}/{entity.id}")

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml; charset=utf-8"
    assert "content-disposition" not in response.headers
    assert response.text == XmlReport().build(entity).text


# Подготовка
@pytest.mark.parametrize(
    ("response_format", "media_type"),
    [("txt", "text/plain; charset=utf-8"), ("xml", "application/xml; charset=utf-8"), ("html", "text/html; charset=utf-8")],
)
def test_get_entity_report_text_format_returns_inline_text(
    client: TestClient, first_start_storage: StorageManager, response_format: str, media_type: str
):
    """TXT, XML и HTML отдаются структурированным текстом со своим MIME-типом, а не файлом на скачивание."""
    # Подготовка
    recipe = _entity(first_start_storage, EntityType.RECIPE)

    # Действие
    response = client.get(f"/api/reports/{response_format}/recipe/{recipe.id}")

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert "content-disposition" not in response.headers
    assert "Борщ с говядиной" in response.text


# Подготовка
@pytest.mark.parametrize(
    ("response_format", "extension", "report_type"),
    [("markdown", "md", MarkdownReport), ("csv", "csv", CsvReport)],
    ids=["markdown", "csv"],
)
def test_get_entity_report_binary_format_returns_file_attachment(
    client: TestClient,
    first_start_storage: StorageManager,
    response_format: str,
    extension: str,
    report_type: type[AbstractReport],
):
    """Markdown и CSV отдаются файлом: заголовок attachment с именем по типу и коду, тело — байты отчёта."""
    # Подготовка
    recipe = _entity(first_start_storage, EntityType.RECIPE)

    # Действие
    response = client.get(f"/api/reports/{response_format}/recipe/{recipe.id}")

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-disposition"] == f'attachment; filename="recipe-{recipe.id}.{extension}"'
    assert response.content == report_type().build(recipe).binary


def test_get_entity_report_unknown_id_returns_not_found(client: TestClient):
    """Для кода, которого нет среди сущностей типа, возвращается 404 с кодом в тексте ошибки."""
    # Подготовка
    entity_id = uuid.uuid4()

    # Действие
    response = client.get(f"/api/reports/txt/nomenclature/{entity_id}")

    # Проверка
    assert response.status_code == 404
    assert str(entity_id) in response.json()["detail"]


def test_get_entity_report_id_of_other_type_returns_not_found(client: TestClient, first_start_storage: StorageManager):
    """Код единицы измерения не находит номенклатуру: поиск идёт только среди сущностей указанного типа."""
    # Подготовка
    kilogram = _entity(first_start_storage, EntityType.RANGE)

    # Действие
    response = client.get(f"/api/reports/txt/nomenclature/{kilogram.id}")

    # Проверка
    assert response.status_code == 404


# Подготовка
@pytest.mark.parametrize(
    "path",
    [
        f"/api/reports/pdf/recipe/{uuid.uuid4()}",
        f"/api/reports/txt/warehouse/{uuid.uuid4()}",
        "/api/reports/txt/recipe/not-a-uuid",
        "/api/reports/recipe/not-a-uuid",
    ],
    ids=["unknown_format", "unknown_type", "invalid_id", "default_invalid_id"],
)
def test_get_entity_report_invalid_path_returns_unprocessable_entity(client: TestClient, path: str):
    """Формат или тип не из перечислений и код не в виде UUID FastAPI отвергает с ответом 422."""
    # Действие
    response = client.get(path)

    # Проверка
    assert response.status_code == 422


def test_get_entity_default_report_txt_settings_returns_txt(client: TestClient, first_start_storage: StorageManager):
    """Без формата в пути отчёт строится create_default: при настройках по умолчанию это TXT."""
    # Подготовка
    beet = _entity(first_start_storage, EntityType.NOMENCLATURE)

    # Действие
    response = client.get(f"/api/reports/nomenclature/{beet.id}")

    # Проверка
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.text == TxtReport().build(beet).text


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_get_entity_default_report_format_in_settings_returns_that_format(
    load_settings: Callable[..., None], response_format: ResponseFormat
):
    """Формат отчёта без формата в пути берётся из response_format настроек."""
    # Подготовка
    load_settings(True, response_format.value)
    storage = StorageManager()
    storage.load()
    kilogram = _entity(storage, EntityType.RANGE)

    # Действие
    with TestClient(app) as client:
        default = client.get(f"/api/reports/range/{kilogram.id}")
        explicit = client.get(f"/api/reports/{response_format.value}/range/{kilogram.id}")

    # Проверка
    assert default.status_code == 200
    assert default.headers["content-type"] == explicit.headers["content-type"]
    assert default.content == explicit.content


def test_get_entity_default_report_unknown_id_returns_not_found(client: TestClient):
    """Отчёт по умолчанию для несуществующего кода возвращает 404."""
    # Действие
    response = client.get(f"/api/reports/range/{uuid.uuid4()}")

    # Проверка
    assert response.status_code == 404
