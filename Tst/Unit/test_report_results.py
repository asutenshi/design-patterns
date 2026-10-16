import pytest
from Src.Core.abstract_text_report_result import AbstractTextReportResult
from Src.Core.exception import ArgumentsException
from Src.Dtos.csv_report_result import CsvReportResult
from Src.Dtos.html_report_result import HtmlReportResult
from Src.Dtos.markdown_report_result import MarkdownReportResult
from Src.Dtos.txt_report_result import TxtReportResult
from Src.Dtos.xml_report_result import XmlReportResult

# Результаты всех форматов. Подробные проверки TXT — в test_txt_report_result
RESULT_TYPES: list[type[AbstractTextReportResult]] = [
    TxtReportResult,
    MarkdownReportResult,
    CsvReportResult,
    XmlReportResult,
    HtmlReportResult,
]


# Подготовка
@pytest.mark.parametrize(
    ("result_type", "is_binary", "media_type", "file_extension"),
    [
        (TxtReportResult, False, "text/plain; charset=utf-8", "txt"),
        (MarkdownReportResult, True, "text/markdown; charset=utf-8", "md"),
        (CsvReportResult, True, "text/csv; charset=utf-8", "csv"),
        (XmlReportResult, False, "application/xml; charset=utf-8", "xml"),
        (HtmlReportResult, False, "text/html; charset=utf-8", "html"),
    ],
    ids=lambda item: item.__name__ if isinstance(item, type) else "",
)
def test_properties_format_returns_delivery_settings(
    result_type: type[AbstractTextReportResult], is_binary: bool, media_type: str, file_extension: str
):
    """Markdown и CSV отдаются файлом, остальные форматы — текстом; у каждого свой MIME-тип и расширение."""
    # Действие
    result = result_type("отчёт")

    # Проверка
    assert result.is_binary is is_binary
    assert result.media_type == media_type
    assert result.file_extension == file_extension


# Подготовка
@pytest.mark.parametrize(
    "result_type", [MarkdownReportResult, XmlReportResult, HtmlReportResult], ids=lambda item: item.__name__
)
def test_binary_text_format_returns_utf8_without_bom(result_type: type[AbstractTextReportResult]):
    """Байты результата — его текст в UTF-8 без метки порядка байтов."""
    # Подготовка
    text = "name: Борщ"

    # Действие
    result = result_type(text)

    # Проверка
    assert result.text == text
    assert result.binary == text.encode("utf-8")


def test_binary_csv_returns_utf8_with_bom_and_text_without_it():
    """CSV отдаётся байтами с меткой UTF-8 для Excel, а текст метки не содержит."""
    # Подготовка
    text = "field;value\r\nname;Борщ\r\n"

    # Действие
    result = CsvReportResult(text)

    # Проверка
    assert result.text == text
    assert result.binary == b"\xef\xbb\xbf" + text.encode("utf-8")


# Подготовка
@pytest.mark.parametrize("result_type", RESULT_TYPES, ids=lambda item: item.__name__)
def test_init_not_string_raises_arguments_exception(result_type: type[AbstractTextReportResult]):
    """Содержимое, не являющееся строкой, отвергается в любом формате."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = result_type(b"bytes")  # pyright: ignore[reportArgumentType]


def test_eq_same_text_different_formats_are_not_equal():
    """Результаты разных форматов не равны, даже если совпадает текст: равенство учитывает тип."""
    # Действие и проверка
    assert MarkdownReportResult("отчёт") != TxtReportResult("отчёт")
    assert XmlReportResult("отчёт") == XmlReportResult("отчёт")
