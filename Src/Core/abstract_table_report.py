from abc import ABC, abstractmethod
from typing import ClassVar

from Src.Dtos.report_result import ReportResult
from Src.Dtos.table_dto import TableDto


class AbstractTableReport(ABC):
    """Абстрактный табличный отчёт: превращает ``TableDto`` в ``ReportResult`` нужного формата."""

    # Кодировка байтового представления результата
    _ENCODING: ClassVar[str] = "utf-8"

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Возвращает True, если результат отдаётся файлом на скачивание."""

    @property
    @abstractmethod
    def media_type(self) -> str:
        """Возвращает MIME-тип результата."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Возвращает расширение файла без точки."""

    @abstractmethod
    def build(self, table: TableDto) -> ReportResult:
        """Формирует табличный отчёт.

        :param table: Заголовки и строки таблицы.
        :return: Результат выгрузки с содержимым и параметрами HTTP-ответа.
        :raises ArgumentsException: Если ``table`` не является ``TableDto``.
        """

    def _result(self, text: str) -> ReportResult:
        """Оборачивает текст отчёта в ``ReportResult`` со свойствами этого формата.

        :param text: Сформированный текст таблицы.
        :return: Готовый результат выгрузки.
        """
        return ReportResult(
            text, self.media_type, self.file_extension, is_binary=self.is_binary, encoding=self._ENCODING
        )
