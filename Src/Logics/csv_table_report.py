import csv
import io
from typing import ClassVar, override

from Src.Core.abstract_table_report import AbstractTableReport
from Src.Core.common_validator import CommonValidator
from Src.Dtos.report_result import ReportResult
from Src.Dtos.table_dto import TableDto


class CsvTableReport(AbstractTableReport):
    """Табличный отчёт в формате CSV для скачивания и открытия в Excel.

    Использует точку с запятой как разделитель и кодировку ``utf-8-sig`` с меткой порядка байтов,
    чтобы Excel с русской локалью корректно открывал кириллицу и колонки без ручной настройки.
    """

    # UTF-8 с BOM для корректной кириллицы в Excel
    _ENCODING: ClassVar[str] = "utf-8-sig"
    # Разделитель колонок
    _DELIMITER: str = ";"

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает True: CSV-выгрузка скачивается готовым файлом."""
        return True

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип CSV в UTF-8."""
        return "text/csv; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение csv."""
        return "csv"

    @override
    def build(self, table: TableDto) -> ReportResult:
        """Формирует CSV-таблицу с заголовком и строками данных.

        :param table: Исходная таблица.
        :return: Результат выгрузки в формате CSV.
        :raises ArgumentsException: Если передан не ``TableDto``.
        """
        table = CommonValidator.validate_instance(table, TableDto, "table", "Ожидается таблица TableDto")
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=self._DELIMITER)
        writer.writerow(table.headers)
        writer.writerows(table.rows)
        return self._result(buffer.getvalue())
