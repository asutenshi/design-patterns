from typing import override

from Src.Core.abstract_text_report_result import AbstractTextReportResult


class TxtReportResult(AbstractTextReportResult):
    """Результат отчёта в формате простого текста. Отдаётся текстом, а не файлом."""

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: текстовый отчёт отдаётся текстом."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип простого текста в кодировке UTF-8."""
        return "text/plain; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла простого текста."""
        return "txt"
