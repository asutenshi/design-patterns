import uuid
from abc import ABC, abstractmethod
from enum import Enum

from Src.Core.abstract_report_result import AbstractReportResult
from Src.Core.common import Common
from Src.Core.named_entity import NamedEntity


class AbstractReport(ABC):
    """Абстрактный отчёт: формирует результат по сущности в своём формате.

    У каждого формата свой наследник со своей реализацией ``build()`` и своим результатом.
    Общие для всех форматов правила обхода сущности заданы здесь, чтобы форматы выводили
    одни и те же данные:

    - поля объекта — его публичные свойства (``Common.get_fields``), в порядке объявления;
    - вложенная сущность с наименованием выводится ссылкой (наименование и код), а не целиком:
      она живёт в хранилище сама по себе, а раскрытие ссылок зацикливается
      (у базовой единицы ``RangeModel.base`` — она сама);
    - остальные вложенные объекты раскрываются по дереву «Компоновщика»: состав карты
      (``RecipeModel.items``) и основание ингредиента (``IngredientModel.base``);
    - простые значения (строки, числа, перечисления, коды) приводятся к строке ``_format_scalar()``.
    """

    # Число знаков после запятой для дробных чисел: веса считаются в граммах
    _FLOAT_PRECISION: int = 3

    @abstractmethod
    def build(self, source: NamedEntity) -> AbstractReportResult:
        """Формирует отчёт по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат в формате отчёта.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """

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
