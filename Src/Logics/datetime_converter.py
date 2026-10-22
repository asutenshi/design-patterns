from datetime import date
from typing import override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException


class DatetimeConverter(AbstractConverter):
    """Конвертер дат: дата и дата со временем записываются строкой ISO 8601.

    JSON не знает дат, а строка ISO 8601 однозначно читается обратно (``datetime.fromisoformat``).
    """

    @override
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает дату в словарь «наименование поля — строка ISO 8601».

        :param field: Наименование поля, ключ результата.
        :param value: Дата (``date``) или дата со временем (``datetime``).
        :return: Словарь ``{field: "2026-10-22T12:30:00"}``, у даты без времени — ``{field: "2026-10-22"}``.
        :raises ArgumentsException: Если наименование поля некорректно или значение не дата.
        """
        # datetime — наследник date, поэтому одна проверка покрывает оба типа
        if not isinstance(value, date):
            raise ArgumentsException("value", "Ожидается дата")

        return self._entry(field, value.isoformat())
