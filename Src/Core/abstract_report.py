import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum
from typing import ClassVar, TypeGuard

from Src.Core.common import Common
from Src.Core.named_entity import NamedEntity
from Src.Dtos.report_result import ReportResult


class AbstractReport(ABC):
    """Абстрактный отчёт: формирует результат по сущности в своём формате.

    У каждого формата свой наследник со своей реализацией ``build()``. Наследник же знает,
    как отдавать свой результат: файлом или текстом (``is_binary``), с каким MIME-типом
    (``media_type``) и расширением (``file_extension``). Общие для всех форматов правила обхода сущности заданы здесь, чтобы форматы выводили
    одни и те же данные:

    - поля объекта — его публичные свойства (``Common.get_fields``), в порядке объявления;
    - вложенная сущность с наименованием выводится ссылкой (наименование и код), а не целиком:
      она живёт в хранилище сама по себе, а раскрытие ссылок зацикливается
      (у базовой единицы ``RangeModel.base`` — она сама);
    - остальные вложенные объекты раскрываются по дереву «Компоновщика»: состав карты
      (``RecipeModel.items``) и основание ингредиента (``IngredientModel.base``);
    - список или кортеж (``_is_collection()``) выводится поэлементно по тем же правилам;
    - простые значения (строки, числа, перечисления, коды) приводятся к строке ``_format_scalar()``,
      ссылка в текстовом виде — ``_format_reference()``.
    """

    # Число знаков после запятой для дробных чисел: веса считаются в граммах
    _FLOAT_PRECISION: int = 3
    # Кодировка, в которой текст отчёта отдаётся байтами
    _ENCODING: ClassVar[str] = "utf-8"

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Возвращает True, если отчёт отдаётся файлом на скачивание, а не текстом."""

    @property
    @abstractmethod
    def media_type(self) -> str:
        """Возвращает MIME-тип отчёта, например ``text/plain; charset=utf-8``."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Возвращает расширение файла с отчётом без точки, например ``txt``."""

    @abstractmethod
    def build(self, source: NamedEntity) -> ReportResult:
        """Формирует отчёт по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат в формате отчёта.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """

    def _result(self, text: str) -> ReportResult:
        """Оформляет текст отчёта результатом со способом выдачи формата.

        :param text: Содержимое отчёта.
        :return: Результат с признаками выдачи этого отчёта.
        """
        return ReportResult(
            text, self.media_type, self.file_extension, is_binary=self.is_binary, encoding=self._ENCODING
        )

    @staticmethod
    def _fields(source: object) -> list[tuple[str, object]]:
        """Возвращает пары «имя поля — значение» для публичных свойств объекта.

        :param source: Раскрываемый объект.
        :return: Поля в порядке объявления, сначала поля базовых классов.
        """
        return [(field, getattr(source, field)) for field in Common.get_fields(source)]

    @staticmethod
    def _is_scalar(value: object) -> bool:
        """Проверяет, что значение простое и выводится одной строкой.

        :param value: Проверяемое значение.
        :return: True для None, строк, чисел, bool, перечислений и UUID.
        """
        return value is None or isinstance(value, (str, int, float, Enum, uuid.UUID))

    @staticmethod
    def _is_reference(value: object) -> bool:
        """Проверяет, что вложенное значение выводится ссылкой, а не раскрывается.

        :param value: Значение поля или элемент списка.
        :return: True для сущности с наименованием.
        """
        return isinstance(value, NamedEntity)

    @staticmethod
    def _is_collection(value: object) -> TypeGuard[Sequence[object]]:
        """Проверяет, что значение — список элементов, который выводится поэлементно.

        :param value: Значение поля или элемент списка.
        :return: True для списка и кортежа.
        """
        return isinstance(value, (list, tuple))

    @staticmethod
    def _format_reference(entity: NamedEntity) -> str:
        """Возвращает текст ссылки на сущность.

        :param entity: Сущность, на которую ссылается поле.
        :return: Строка ``наименование [код]``.
        """
        return f"{entity.name} [{entity.id}]"

    @staticmethod
    def _format_scalar(value: object) -> str:
        """Приводит простое значение к строке.

        Перечисление выводится значением, дробное число — с округлением
        до ``_FLOAT_PRECISION`` знаков без хвостовых нулей, None — пустой строкой.

        :param value: Простое значение (см. ``_is_scalar``).
        :return: Строковое представление.
        """
        if value is None:
            return ""
        if isinstance(value, Enum):
            return str(value.value)  # pyright: ignore[reportAny]
        if isinstance(value, float):
            text = f"{value:.{AbstractReport._FLOAT_PRECISION}f}".rstrip("0").rstrip(".")
            # Округление крошечного отрицательного числа даёт «-0»
            return "0" if text == "-0" else text
        return str(value)
