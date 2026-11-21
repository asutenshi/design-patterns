from datetime import date
from typing import cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Dtos.turnover_row import TurnoverRow


class TurnoverReport:
    """Оборотно-сальдовая ведомость (ОСВ): период и строки «номенклатура + склад».

    Период принадлежит отчёту целиком, а не строке: у всех строк он один. Границы уже вычислены
    (``TurnoverService`` подставил первую запись и сегодняшний день), поэтому здесь они всегда заданы.
    Отчёт отдаёт данные предметной области, а формат ответа выбирает тот, кто его показывает
    (``ConverterFactory`` для JSON).
    """

    # Первый день периода включительно
    _start: date
    # Последний день периода включительно
    _end: date
    # Строки ведомости
    _rows: tuple[TurnoverRow, ...]

    def __init__(self, start: date, end: date, rows: list[TurnoverRow]) -> None:
        """Инициализирует ОСВ.

        :param start: Первый день периода включительно.
        :param end: Последний день периода включительно.
        :param rows: Строки ведомости, список может быть пустым.
        :raises ArgumentsException: Если границы не даты, начало позже конца или строка неверного типа.
        """
        self._start = CommonValidator.validate_date(start, "start")
        self._end = CommonValidator.validate_date(end, "end")
        if self._start > self._end:
            raise ArgumentsException("start", f"Начало периода {self._start} позже конца {self._end}")
        items = cast(list[object], CommonValidator.validate_instance(rows, list, "rows", "Ожидается список строк"))
        self._rows = tuple(
            CommonValidator.validate_instance(item, TurnoverRow, "rows", "Ожидается строка ОСВ") for item in items
        )

    @property
    def start(self) -> date:
        """Возвращает первый день периода."""
        return self._start

    @property
    def end(self) -> date:
        """Возвращает последний день периода."""
        return self._end

    @property
    def rows(self) -> list[TurnoverRow]:
        """Возвращает копию списка строк ведомости."""
        return list(self._rows)
