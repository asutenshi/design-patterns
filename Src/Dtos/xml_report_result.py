from typing import override

from Src.Core.abstract_text_report_result import AbstractTextReportResult


class XmlReportResult(AbstractTextReportResult):
    """Результат отчёта в формате XML. Отдаётся структурированным текстом, а не файлом."""

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: документ XML отдаётся текстом."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип XML в кодировке UTF-8."""
        return "application/xml; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла XML."""
        return "xml"
