import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.table_export_format import TableExportFormat
from Src.Dtos.table_dto import TableDto
from Src.Logics.table_report_factory import TableReportFactory


def _sample_table() -> TableDto:
    """Возвращает учебную таблицу лога с двумя строками."""
    return TableDto(
        headers=["Период", "Название подсистемы", "Тип сообщения", "Сообщение"],
        rows=[
            ["2026-11-26T10:00:00", "CRUD", "INFO", "Создан склад"],
            ["2026-11-26T10:05:00", "WEB", "ERROR", "GET /missing | 404"],
        ],
    )


def test_table_dto_row_length_mismatch_raises():
    """Строка с неверным числом колонок отклоняется исключением ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TableDto(["Колонка 1", "Колонка 2"], [["только одна"]])


def test_table_dto_empty_headers_raises():
    """Таблица без заголовков не допускается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TableDto([], [])


def test_txt_table_report_builds_downloadable_file():
    """TXT-выгрузка отдаётся файлом с выровненной таблицей и расширением txt."""
    # Подготовка
    report = TableReportFactory().create(TableExportFormat.TXT)

    # Действие
    result = report.build(_sample_table())

    # Проверка
    assert result.is_binary is True
    assert result.file_extension == "txt"
    assert "Период" in result.text
    assert "Создан склад" in result.text


def test_csv_table_report_builds_excel_ready_file_with_bom():
    """CSV-выгрузка отдаётся файлом с BOM UTF-8 и разделителем точка с запятой."""
    # Подготовка
    report = TableReportFactory().create(TableExportFormat.CSV)

    # Действие
    result = report.build(_sample_table())

    # Проверка
    assert result.is_binary is True
    assert result.file_extension == "csv"
    assert result.binary.startswith(b"\xef\xbb\xbf")
    assert "Период;Название подсистемы;Тип сообщения;Сообщение" in result.text
    assert "2026-11-26T10:00:00;CRUD;INFO;Создан склад" in result.text


def test_markdown_table_report_builds_inline_text_and_escapes_pipes():
    """Markdown-выгрузка отдаётся текстом в браузер и экранирует вертикальную черту в ячейках."""
    # Подготовка
    report = TableReportFactory().create(TableExportFormat.MARKDOWN)

    # Действие
    result = report.build(_sample_table())

    # Проверка
    assert result.is_binary is False
    assert result.file_extension == "md"
    assert "| Период | Название подсистемы | Тип сообщения | Сообщение |" in result.text
    assert "| --- | --- | --- | --- |" in result.text
    assert r"GET /missing \| 404" in result.text
