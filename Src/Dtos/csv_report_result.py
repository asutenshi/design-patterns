from typing import ClassVar, override

from Src.Core.abstract_text_report_result import AbstractTextReportResult


class CsvReportResult(AbstractTextReportResult):
    """Результат отчёта в формате CSV. Отдаётся файлом на скачивание.

    Байты начинаются с метки порядка байтов UTF-8: без неё Excel открывает файл
    в кодировке системы и кириллица превращается в «кракозябры». Текст метки не содержит.
    """

    # UTF-8 с меткой порядка байтов
    _ENCODING: ClassVar[str] = "utf-8-sig"

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает True: таблица CSV отдаётся файлом."""
        return True

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип CSV в кодировке UTF-8."""
        return "text/csv; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла CSV."""
        return "csv"
