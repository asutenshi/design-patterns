from typing import override

from Src.Core.abstract_table_report import AbstractTableReport
from Src.Core.common_validator import CommonValidator
from Src.Dtos.report_result import ReportResult
from Src.Dtos.table_dto import TableDto


class MarkdownTableReport(AbstractTableReport):
    """Табличный отчёт в формате Markdown для просмотра текстом в браузере."""

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: Markdown-таблица отдаётся текстом в браузер."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип Markdown в UTF-8."""
        return "text/markdown; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение md."""
        return "md"

    @override
    def build(self, table: TableDto) -> ReportResult:
        """Формирует таблицу в синтаксисе GitHub Flavored Markdown.

        :param table: Исходная таблица.
        :return: Результат выгрузки в формате Markdown.
        :raises ArgumentsException: Если передан не ``TableDto``.
        """
        table = CommonValidator.validate_instance(table, TableDto, "table", "Ожидается таблица TableDto")
        header_line = self._format_row(table.headers)
        divider = "| " + " | ".join("---" for _ in table.headers) + " |"
        data_lines = [self._format_row(row) for row in table.rows]
        return self._result("\n".join([header_line, divider, *data_lines]))

    def _format_row(self, row: tuple[str, ...]) -> str:
        """Оформляет строку Markdown-таблицы с экранированием спецсимволов."""
        return "| " + " | ".join(self._escape(cell) for cell in row) + " |"

    @staticmethod
    def _escape(value: str) -> str:
        """Экранирует вертикальную черту и убирает переводы строк, ломающие таблицу."""
        return value.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
