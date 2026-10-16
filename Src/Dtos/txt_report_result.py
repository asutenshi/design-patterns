from typing import override

from Src.Core.abstract_report_result import AbstractReportResult
from Src.Core.common_validator import CommonValidator


class TxtReportResult(AbstractReportResult):
    """Результат отчёта в формате простого текста. Отдаётся текстом, а не файлом."""

    # Содержимое отчёта
    _text: str

    def __init__(self, text: str) -> None:
        """Инициализирует результат.

        :param text: Содержимое отчёта. Пустая строка допустима: отчёт без данных.
        :raises ArgumentsException: Если значение не строка.
        """
        self._text = CommonValidator.validate_instance(text, str, "text", "Ожидается строка")

    @property
    @override
    def text(self) -> str:
        """Возвращает содержимое отчёта текстом."""
        return self._text

    @property
    @override
    def binary(self) -> bytes:
        """Возвращает содержимое отчёта в кодировке UTF-8."""
        return self._text.encode("utf-8")

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
