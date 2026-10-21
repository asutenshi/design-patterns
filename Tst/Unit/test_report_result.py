import pytest
from Src.Core.abstract_report import AbstractReport
from Src.Core.exception import ArgumentsException
from Src.Dtos.report_result import ReportResult
from Src.Logics.csv_report import CsvReport
from Src.Logics.html_report import HtmlReport
from Src.Logics.markdown_report import MarkdownReport
from Src.Logics.storage_manager import StorageManager
from Src.Logics.txt_report import TxtReport
from Src.Logics.xml_report import XmlReport


def create_result(text: str = "отчёт", *, is_binary: bool = False) -> ReportResult:
    """Создаёт результат текстового отчёта с типичными признаками выдачи."""
    return ReportResult(text, "text/plain; charset=utf-8", "txt", is_binary=is_binary)


def test_init_text_returns_text_and_utf8_binary():
    """Текст отдаётся как есть, байты — тот же текст в UTF-8."""
    # Подготовка
    text = "name: Борщ"

    # Действие
    result = create_result(text)

    # Проверка
    assert result.text == text
    assert result.binary == text.encode("utf-8")


def test_init_empty_text_is_allowed():
    """Пустой отчёт допустим: данных может не быть."""
    # Действие
    result = create_result("")

    # Проверка
    assert result.text == ""
    assert result.binary == b""


def test_init_encoding_utf8_sig_returns_bom_in_binary_only():
    """Кодировка с меткой порядка байтов добавляет метку в байты, а текст её не содержит."""
    # Подготовка
    text = "field;value\r\nname;Борщ\r\n"

    # Действие
    result = ReportResult(text, "text/csv; charset=utf-8", "csv", is_binary=True, encoding="utf-8-sig")

    # Проверка
    assert result.text == text
    assert result.binary == b"\xef\xbb\xbf" + text.encode("utf-8")


def test_properties_init_values_returns_delivery_settings():
    """Признаки выдачи — те, что переданы при создании."""
    # Действие
    result = ReportResult("отчёт", "text/markdown; charset=utf-8", "md", is_binary=True)

    # Проверка
    assert result.is_binary is True
    assert result.media_type == "text/markdown; charset=utf-8"
    assert result.file_extension == "md"


# Подготовка
@pytest.mark.parametrize("text", [None, 1, b"bytes", ["строка"]])
def test_init_not_string_text_raises_arguments_exception(text: object):
    """Содержимое, не являющееся строкой, отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportResult(text, "text/plain", "txt", is_binary=False)  # pyright: ignore[reportArgumentType]


# Подготовка
@pytest.mark.parametrize(
    ("media_type", "file_extension", "is_binary", "encoding"),
    [
        ("", "txt", False, "utf-8"),
        (None, "txt", False, "utf-8"),
        ("text/plain", "  ", False, "utf-8"),
        ("text/plain", 1, False, "utf-8"),
        ("text/plain", "txt", 1, "utf-8"),
        ("text/plain", "txt", False, ""),
    ],
)
def test_init_invalid_delivery_settings_raises_arguments_exception(
    media_type: object, file_extension: object, is_binary: object, encoding: object
):
    """Пустые или неверного типа MIME-тип, расширение, признак файла и кодировка отвергаются."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportResult(
            "отчёт",
            media_type,  # pyright: ignore[reportArgumentType]
            file_extension,  # pyright: ignore[reportArgumentType]
            is_binary=is_binary,  # pyright: ignore[reportArgumentType]
            encoding=encoding,  # pyright: ignore[reportArgumentType]
        )


def test_eq_same_content_results_are_equal_and_have_same_hash():
    """Результаты с одинаковым содержимым и способом выдачи равны и одинаково хэшируются."""
    # Подготовка
    first = create_result()
    second = create_result()

    # Действие и проверка
    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_eq_different_text_results_are_not_equal():
    """Результаты с разным содержимым не равны."""
    # Действие и проверка
    assert create_result("отчёт 1") != create_result("отчёт 2")


def test_eq_same_text_different_delivery_are_not_equal():
    """Результаты с одним текстом, но разным способом выдачи не равны."""
    # Действие и проверка
    assert create_result(is_binary=True) != create_result(is_binary=False)
    assert create_result() != ReportResult("отчёт", "application/xml", "xml", is_binary=False)


def test_eq_result_and_other_type_are_not_equal():
    """Результат не равен значению другого типа, даже если совпадает текст."""
    # Действие и проверка
    assert create_result("отчёт") != "отчёт"


def test_to_response_text_result_returns_text_body_without_attachment():
    """Текстовый результат отдаётся телом ответа с MIME-типом формата, без скачивания."""
    # Подготовка
    result = create_result("name: Борщ")

    # Действие
    response = result.to_response("recipe-1")

    # Проверка
    assert response.body == "name: Борщ".encode()
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "content-disposition" not in response.headers


def test_to_response_binary_result_returns_bytes_as_attachment():
    """Двоичный результат отдаётся байтами с заголовком скачивания и расширением формата."""
    # Подготовка
    result = ReportResult("a;b\r\n", "text/csv; charset=utf-8", "csv", is_binary=True, encoding="utf-8-sig")

    # Действие
    response = result.to_response("recipe-1")

    # Проверка
    assert response.body == b"\xef\xbb\xbfa;b\r\n"
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="recipe-1.csv"'


# Подготовка
@pytest.mark.parametrize(
    ("report_type", "is_binary", "media_type", "file_extension"),
    [
        (TxtReport, False, "text/plain; charset=utf-8", "txt"),
        (MarkdownReport, True, "text/markdown; charset=utf-8", "md"),
        (CsvReport, True, "text/csv; charset=utf-8", "csv"),
        (XmlReport, False, "application/xml; charset=utf-8", "xml"),
        (HtmlReport, False, "text/html; charset=utf-8", "html"),
    ],
    ids=lambda item: item.__name__ if isinstance(item, type) else "",
)
def test_properties_report_returns_delivery_settings(
    report_type: type[AbstractReport], is_binary: bool, media_type: str, file_extension: str
):
    """Markdown и CSV отдаются файлом, остальные форматы — текстом; у каждого свой MIME-тип и расширение."""
    # Действие
    report = report_type()

    # Проверка
    assert report.is_binary is is_binary
    assert report.media_type == media_type
    assert report.file_extension == file_extension


def test_build_csv_report_returns_utf8_bom_in_binary_and_none_in_text(first_start_storage: StorageManager):
    """Байты CSV начинаются с метки порядка байтов UTF-8 для Excel, а текст метки не содержит."""
    # Подготовка
    unit = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    result = CsvReport().build(unit)

    # Проверка
    assert result.binary.startswith(b"\xef\xbb\xbf")
    assert not result.text.startswith("﻿")
    assert result.binary == b"\xef\xbb\xbf" + result.text.encode("utf-8")
