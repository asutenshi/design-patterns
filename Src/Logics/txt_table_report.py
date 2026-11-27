from typing import override

from Src.Core.abstract_table_report import AbstractTableReport
from Src.Core.common_validator import CommonValidator
from Src.Dtos.report_result import ReportResult
from Src.Dtos.table_dto import TableDto


class TxtTableReport(AbstractTableReport):
    """Табличный отчёт в формате TXT для скачивания и просмотра в текстовом редакторе."""

    # Разделитель колонок в текстовой строке
    _SEPARATOR: str = " | "

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает True: TXT-выгрузка скачивается готовым файлом."""
        return True

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип простого текста в UTF-8."""
        return "text/plain; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение txt."""
        return "txt"

    @override
    def build(self, table: TableDto) -> ReportResult:
        """Формирует выровненную текстовую таблицу.

        :param table: Исходная таблица.
        :return: Результат выгрузки в формате TXT.
        :raises ArgumentsException: Если передан не ``TableDto``.
        """
        table = CommonValidator.validate_instance(table, TableDto, "table", "Ожидается таблица TableDto")
        all_rows = [table.headers, *table.rows]
        widths = [max(len(self._clean(row[idx])) for row in all_rows) for idx in range(len(table.headers))]

        header_line = self._format_row(table.headers, widths)
        divider = "-+-".join("-" * width for width in widths)
        data_lines = [self._format_row(row, widths) for row in table.rows]
        return self._result("\n".join([header_line, divider, *data_lines]))

    def _format_row(self, row: tuple[str, ...], widths: list[int]) -> str:
        """Выравнивает ячейки строки по ширине колонок."""
        cells = [self._clean(cell).ljust(width) for cell, width in zip(row, widths, strict=True)]
        return self._SEPARATOR.join(cells).rstrip()

    @staticmethod
    def _clean(value: str) -> str:
        """Заменяет переводы строк на пробелы, чтобы запись занимала одну строку."""
        return value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
