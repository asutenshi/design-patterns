from typing import override

from Src.Core.abstract_text_report_result import AbstractTextReportResult


class HtmlReportResult(AbstractTextReportResult):
    """Результат отчёта в формате HTML. Отдаётся страницей, а не файлом."""

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: страница HTML отдаётся текстом."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип HTML в кодировке UTF-8."""
        return "text/html; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла HTML."""
        return "html"
