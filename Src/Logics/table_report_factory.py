from typing import ClassVar

from Src.Core.abstract_table_report import AbstractTableReport
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.table_export_format import TableExportFormat
from Src.Logics.csv_table_report import CsvTableReport
from Src.Logics.markdown_table_report import MarkdownTableReport
from Src.Logics.txt_table_report import TxtTableReport


class TableReportFactory:
    """Фабрика табличных отчётов: выбирает реализацию по ``TableExportFormat``."""

    # Сопоставление формата и класса табличного отчёта
    _reports: ClassVar[dict[TableExportFormat, type[AbstractTableReport]]] = {
        TableExportFormat.TXT: TxtTableReport,
        TableExportFormat.CSV: CsvTableReport,
        TableExportFormat.MARKDOWN: MarkdownTableReport,
    }

    def create(self, export_format: TableExportFormat) -> AbstractTableReport:
        """Создаёт табличный отчёт указанного формата.

        :param export_format: Формат табличной выгрузки.
        :return: Экземпляр табличного отчёта.
        :raises ArgumentsException: Если формат не является ``TableExportFormat`` или не поддержан.
        """
        export_format = CommonValidator.validate_instance(
            export_format, TableExportFormat, "export_format", "Ожидается формат табличной выгрузки"
        )
        report_class = self._reports.get(export_format)
        if report_class is None:
            raise ArgumentsException("export_format", f"Формат {export_format.value} не реализован")
        return report_class()
