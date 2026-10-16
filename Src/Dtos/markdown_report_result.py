from typing import override

from Src.Core.abstract_text_report_result import AbstractTextReportResult


class MarkdownReportResult(AbstractTextReportResult):
    """Результат отчёта в формате Markdown. Отдаётся файлом на скачивание."""

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает True: документ Markdown отдаётся файлом."""
        return True

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип Markdown в кодировке UTF-8."""
        return "text/markdown; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла Markdown."""
        return "md"
