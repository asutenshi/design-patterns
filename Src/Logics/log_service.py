from typing import ClassVar

from Src.Core.common_validator import CommonValidator
from Src.Core.table_export_format import TableExportFormat
from Src.Dtos.log_query_dto import LogQueryDto
from Src.Dtos.report_result import ReportResult
from Src.Dtos.table_dto import TableDto
from Src.Logics.logger_manager import LoggerManager
from Src.Logics.prototype import Prototype
from Src.Logics.sorter import Sorter
from Src.Logics.table_report_factory import TableReportFactory
from Src.Models.log_model import LogModel


class LogService:
    """Сервис выборки и выгрузки логов: связывает ``LoggerManager``, ``Prototype``, ``Sorter`` и табличный экспорт."""

    # Заголовки колонок табличной выгрузки лога
    _HEADERS: ClassVar[list[str]] = ["Период", "Название подсистемы", "Тип сообщения", "Сообщение"]

    # Менеджер, хранящий записи лога
    _logger: LoggerManager
    # Универсальный сортировщик моделей
    _sorter: Sorter
    # Фабрика табличных отчётов
    _report_factory: TableReportFactory

    def __init__(
        self,
        logger: LoggerManager | None = None,
        sorter: Sorter | None = None,
        report_factory: TableReportFactory | None = None,
    ) -> None:
        """Инициализирует сервис работы с логами.

        :param logger: Менеджер логов; ``None`` — единственный экземпляр ``LoggerManager``.
        :param sorter: Сортировщик моделей; ``None`` — новый ``Sorter``.
        :param report_factory: Фабрика табличных отчётов; ``None`` — новая ``TableReportFactory``.
        """
        self._logger = logger if logger is not None else LoggerManager()
        self._sorter = sorter if sorter is not None else Sorter()
        self._report_factory = report_factory if report_factory is not None else TableReportFactory()

    def query(self, request: LogQueryDto | None = None) -> list[LogModel]:
        """Отбирает и при необходимости сортирует записи лога.

        :param request: Условия фильтрации и сортировки; ``None`` — все записи в порядке поступления.
        :return: Список подходящих записей лога.
        :raises ArgumentsException: Если запрос некорректен либо путь поля фильтра или сортировки недоступен.
        """
        query = LogQueryDto() if request is None else CommonValidator.validate_instance(
            request, LogQueryDto, "request", "Ожидается запрос логов"
        )
        entries = Prototype(self._logger.logs).clone(query.filter).data
        if query.sort is not None:
            entries = self._sorter.sort(entries, query.sort)
        return entries

    def export(self, export_format: TableExportFormat, request: LogQueryDto | None = None) -> ReportResult:
        """Формирует выгрузку логов в указанном табличном формате.

        :param export_format: Формат выгрузки: TXT, CSV или Markdown.
        :param request: Необязательные условия фильтрации и сортировки.
        :return: Готовый ``ReportResult`` для выдачи в HTTP-ответе или сохранения в файл.
        :raises ArgumentsException: Если формат или параметры запроса некорректны.
        """
        entries = self.query(request)
        table = self._to_table(entries)
        return self._report_factory.create(export_format).build(table)

    def _to_table(self, entries: list[LogModel]) -> TableDto:
        """Преобразует список записей лога в универсальную таблицу ``TableDto``."""
        rows = [
            [
                entry.period.isoformat(),
                entry.subsystem.value,
                entry.level.value,
                entry.message,
            ]
            for entry in entries
        ]
        return TableDto(self._HEADERS, rows)
