from abc import ABC, abstractmethod
from typing import override


class AbstractReportResult(ABC):
    """Абстрактный результат формирования отчёта: содержимое в одном из форматов.

    У каждого формата свой наследник. Результат — объект-значение: у него нет идентификатора,
    он неизменяем, а равенство определяется типом и содержимым. Поэтому два отчёта по одним
    и тем же данным равны. Если отчёты понадобится хранить, хранимой сущностью станет отдельная
    запись (дата, параметры, ответственный), а результат войдёт в неё полем.

    Содержимое доступно и текстом, и байтами. ``is_binary`` подсказывает, как его отдавать:
    файлом на скачивание или текстом.
    """

    @property
    @abstractmethod
    def text(self) -> str:
        """Возвращает содержимое отчёта текстом."""

    @property
    @abstractmethod
    def binary(self) -> bytes:
        """Возвращает содержимое отчёта байтами."""

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Возвращает True, если результат отдаётся файлом на скачивание, а не текстом."""

    @property
    @abstractmethod
    def media_type(self) -> str:
        """Возвращает MIME-тип содержимого, например ``text/plain; charset=utf-8``."""

    @override
    def __eq__(self, value: object, /) -> bool:
        """Сравнивает результаты по типу и содержимому."""
        if type(value) is not type(self):
            return NotImplemented
        return self.binary == value.binary

    @override
    def __hash__(self) -> int:
        """Возвращает хэш результата на основе типа и содержимого."""
        return hash((type(self), self.binary))
