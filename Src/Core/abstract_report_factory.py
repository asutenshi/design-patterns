from abc import ABC, abstractmethod

from Src.Core.abstract_report import AbstractReport
from Src.Core.response_format import ResponseFormat


class AbstractReportFactory(ABC):
    """Абстрактная фабрика отчётов: создаёт отчёт нужного формата.

    Клиент работает только с AbstractReport и не знает конкретных классов форматов.
    Формат задаётся явно (``create()``) или берётся из настроек фабрики (``create_default()``).
    """

    @abstractmethod
    def create(self, response_format: ResponseFormat) -> AbstractReport:
        """Создаёт отчёт указанного формата.

        :param response_format: Формат отчёта.
        :return: Новый отчёт.
        :raises ArgumentsException: Если значение не формат или для формата нет реализации.
        """

    @abstractmethod
    def create_default(self) -> AbstractReport:
        """Создаёт отчёт в формате по умолчанию из настроек.

        :return: Новый отчёт.
        :raises ArgumentsException: Если для формата из настроек нет реализации.
        """
