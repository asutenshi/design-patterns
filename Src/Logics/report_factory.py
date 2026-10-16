from typing import ClassVar, override

from Src.Core.abstract_report import AbstractReport
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.response_format import ResponseFormat
from Src.Logics.csv_report import CsvReport
from Src.Logics.html_report import HtmlReport
from Src.Logics.markdown_report import MarkdownReport
from Src.Logics.txt_report import TxtReport
from Src.Logics.xml_report import XmlReport
from Src.Models.settings_model import SettingsModel


class ReportFactory(AbstractReportFactory):
    """Фабрика отчётов: по формату выбирает класс отчёта из сопоставления и создаёт его.

    Новый формат подключается строкой в ``_reports``, клиентский код при этом не меняется.
    Фабрика хранит настройки приложения: из них ``create_default()`` берёт формат по умолчанию.
    Настройки — ссылка на модель, поэтому смена формата в ней сразу видна фабрике.
    """

    # Сопоставление формата и класса отчёта
    _reports: ClassVar[dict[ResponseFormat, type[AbstractReport]]] = {
        ResponseFormat.TXT: TxtReport,
        ResponseFormat.MARKDOWN: MarkdownReport,
        ResponseFormat.CSV: CsvReport,
        ResponseFormat.XML: XmlReport,
        ResponseFormat.HTML: HtmlReport,
    }

    # Настройки приложения, источник формата по умолчанию
    _settings: SettingsModel

    def __init__(self, settings: SettingsModel) -> None:
        """Инициализирует фабрику.

        :param settings: Настройки приложения.
        :raises ArgumentsException: Если значение не SettingsModel.
        """
        self._settings = CommonValidator.validate_instance(settings, SettingsModel, "settings", "Ожидаются настройки")

    @property
    def settings(self) -> SettingsModel:
        """Возвращает настройки, с которыми работает фабрика."""
        return self._settings

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

    @override
    def create_default(self) -> AbstractReport:
        """Создаёт отчёт в формате ``response_format`` из настроек.

        :return: Новый отчёт.
        :raises ArgumentsException: Если для формата из настроек нет реализации.
        """
        return self.create(self._settings.response_format)
