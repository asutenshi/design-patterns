from abc import ABC
from typing import ClassVar, override

from Src.Core.abstract_report_result import AbstractReportResult
from Src.Core.common_validator import CommonValidator


class AbstractTextReportResult(AbstractReportResult, ABC):
    """Абстрактный результат текстового формата: хранит текст, байты получает его кодированием.

    Все текущие форматы текстовые, поэтому хранение и кодирование вынесены сюда, а наследник задаёт
    только способ выдачи, MIME-тип и расширение. Формат, который строится сразу байтами
    (например, xlsx), наследует AbstractReportResult напрямую.
    """

    # Кодировка, в которой текст отдаётся байтами
    _ENCODING: ClassVar[str] = "utf-8"

    # Содержимое отчёта
    _text: str

    def __init__(self, text: str) -> None:
        """Инициализирует результат.

        :param text: Содержимое отчёта. Пустая строка допустима: отчёт без данных.
        :raises ArgumentsException: Если значение не строка.
        """
        self._text = CommonValidator.validate_instance(text, str, "text", "Ожидается строка")

    @property
    @override
    def text(self) -> str:
        """Возвращает содержимое отчёта текстом."""
        return self._text

    @property
    @override
    def binary(self) -> bytes:
        """Возвращает содержимое отчёта в кодировке ``_ENCODING``."""
        return self._text.encode(self._ENCODING)
