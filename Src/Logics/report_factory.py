from typing import ClassVar, override

from Src.Core.abstract_report import AbstractReport
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.response_format import ResponseFormat
from Src.Logics.txt_report import TxtReport


class ReportFactory(AbstractReportFactory):
    """Фабрика отчётов: по формату выбирает класс отчёта из сопоставления и создаёт его.

    Новый формат подключается строкой в ``_reports``, клиентский код при этом не меняется.
    """

    # Сопоставление формата и класса отчёта
    _reports: ClassVar[dict[ResponseFormat, type[AbstractReport]]] = {
        ResponseFormat.TXT: TxtReport,
    }

    @override
    def create(self, response_format: ResponseFormat) -> AbstractReport:
        """Создаёт отчёт указанного формата.

        :param response_format: Формат отчёта.
        :return: Новый отчёт.
        :raises ArgumentsException: Если значение не формат или для формата нет реализации.
        """
        response_format = CommonValidator.validate_instance(
            response_format, ResponseFormat, "response_format", "Ожидается формат отчёта"
        )
        report = self._reports.get(response_format)
        if report is None:
            raise ArgumentsException("response_format", f"Формат {response_format.value} не реализован")

        return report()
