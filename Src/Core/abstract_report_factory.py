from abc import ABC, abstractmethod

from Src.Core.abstract_report import AbstractReport
from Src.Core.response_format import ResponseFormat


class AbstractReportFactory(ABC):
    """Абстрактная фабрика отчётов: создаёт отчёт нужного формата.

    Клиент работает только с AbstractReport и не знает конкретных классов форматов.
    """

    @abstractmethod
    def create(self, response_format: ResponseFormat) -> AbstractReport:
        """Создаёт отчёт указанного формата.

        :param response_format: Формат отчёта.
        :return: Новый отчёт.
        :raises ArgumentsException: Если значение не формат или для формата нет реализации.
        """
