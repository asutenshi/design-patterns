from datetime import datetime

from fastapi.testclient import TestClient
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem
from Src.Logics.logger_manager import LoggerManager
from Src.Logics.storage_manager import StorageManager
from Src.main import app
from Src.Models.transaction_model import TransactionModel


def test_logs_api_filters_and_sorts_json():
    """POST /api/logs возвращает отфильтрованные и отсортированные записи лога в JSON."""
    # Подготовка
    with TestClient(app) as client:
        create_response = client.post("/api/entities/warehouse", json={"name": "Склад для теста логов"})
        assert create_response.status_code == 201
        created_id = create_response.json()["id"]
        delete_response = client.delete(f"/api/entities/warehouse/{created_id}")
        assert delete_response.status_code == 204

        # Действие
        response = client.post(
            "/api/logs",
            json={
                "filters": [
                    {"field_name": "subsystem", "filter_type": "EQUALS", "value": LogSubsystem.CRUD.value},
                    {"field_name": "level", "filter_type": "EQUALS", "value": LogLevel.INFO.value},
                ],
                "sort": {"field_name": "period", "direction": "DESC"},
            },
        )

        # Проверка
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        assert all(item["subsystem"] == "CRUD" and item["level"] == "INFO" for item in items)
        assert items[0]["period"] >= items[1]["period"]
        assert "Удалена сущность" in items[0]["message"]
        assert "Создана сущность" in items[1]["message"]


def test_logs_api_captures_all_four_subsystems():
    """Журнал фиксирует события всех четырёх подсистем: CRUD, WAREHOUSE, WEB и SETTINGS."""
    # Подготовка
    with TestClient(app) as client:
        # Действие
        patch_resp = client.patch("/api/settings", json={"response_format": "csv"})
        assert patch_resp.status_code == 200

        crud_resp = client.post("/api/entities/warehouse", json={"name": "Склад аудита"})
        assert crud_resp.status_code == 201

        storage = StorageManager()
        beef = storage.nomenclatures[0]
        warehouse = storage.warehouses[0]
        storage.add_transaction(TransactionModel(beef, warehouse, beef.range, 2, datetime(2026, 11, 26, 16, 0)))

        logs_resp = client.post("/api/logs", json={"filters": []})

        # Проверка
        assert logs_resp.status_code == 200
        subsystems = {item["subsystem"] for item in logs_resp.json()}
        assert subsystems == {"CRUD", "WAREHOUSE", "WEB", "SETTINGS"}


def test_export_logs_txt_and_csv_download_files_markdown_returns_text():
    """TXT и CSV отдаются файлом на скачивание, а Markdown — текстом в браузере."""
    # Подготовка
    with TestClient(app) as client:
        _ = client.post("/api/entities/warehouse", json={"name": "Склад экспорта"})
        query = {"filters": [{"field_name": "subsystem", "filter_type": "EQUALS", "value": "CRUD"}]}

        # Действие
        txt_resp = client.post("/api/logs/txt", json=query)
        csv_resp = client.post("/api/logs/csv", json=query)
        md_resp = client.post("/api/logs/markdown", json=query)

        # Проверка
        assert txt_resp.status_code == 200
        assert 'attachment; filename="logs.txt"' in txt_resp.headers.get("content-disposition", "")
        assert "Склад экспорта" in txt_resp.text

        assert csv_resp.status_code == 200
        assert 'attachment; filename="logs.csv"' in csv_resp.headers.get("content-disposition", "")
        assert csv_resp.content.startswith(b"\xef\xbb\xbf")
        assert "Период;Название подсистемы;Тип сообщения;Сообщение" in csv_resp.text

        assert md_resp.status_code == 200
        assert "content-disposition" not in md_resp.headers
        assert "| Период | Название подсистемы | Тип сообщения | Сообщение |" in md_resp.text
        assert "Склад экспорта" in md_resp.text


def test_logs_api_invalid_sort_field_returns_400():
    """Недоступное поле сортировки возвращает ответ 400."""
    # Подготовка
    with TestClient(app) as client:
        LoggerManager().clear()
        _ = client.get("/api/get_report_formats")

        # Действие
        response = client.post("/api/logs", json={"sort": {"field_name": "unknown_field", "direction": "ASC"}})

        # Проверка
        assert response.status_code == 400
