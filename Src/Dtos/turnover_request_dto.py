from datetime import date
from typing import Self

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Dtos.filter_dto import FilterDto


class TurnoverRequestDto:
    """Запрос оборотно-сальдовой ведомости (ОСВ): период и условия отбора записей журнала.

    Период задаётся отдельными полями, а не условием фильтра: он не отбирает записи, а делит их на колонки.
    Записи до начала периода дают остаток на начало, поэтому Прототип их отбрасывать не должен.
    Обе границы включительные. Отсутствующая граница означает «с первой записи» или «по сегодняшний день»;
    подставляет её ``TurnoverService``, потому что первая запись известна только после отбора.
    """

    # Первый день периода, None — с первой записи
    _start: date | None
    # Последний день периода, None — по сегодняшний день
    _end: date | None
    # Условия отбора записей журнала
    _filter: FilterDto

    def __init__(self, start: date | None, end: date | None, filter_dto: FilterDto) -> None:
        """Инициализирует запрос ОСВ.

        :param start: Первый день периода включительно, None — с первой записи.
        :param end: Последний день периода включительно, None — по сегодняшний день.
        :param filter_dto: Условия отбора записей журнала, набор может быть пустым.
        :raises ArgumentsException: Если границы не даты, начало позже конца или условия неверного типа.
        """
        self._start = None if start is None else CommonValidator.validate_date(start, "start")
        self._end = None if end is None else CommonValidator.validate_date(end, "end")
        if self._start is not None and self._end is not None and self._start > self._end:
            raise ArgumentsException("start", f"Начало периода {self._start} позже конца {self._end}")
        self._filter = CommonValidator.validate_instance(filter_dto, FilterDto, "filter_dto", "Ожидаются условия фильтра")

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт запрос по полям ``start``, ``end`` (необязательны) и ``filters``.

        :param data: Тело запроса: даты строками ``ГГГГ-ММ-ДД`` и условия фильтра в формате ``FilterDto``.
        :return: Новый запрос ОСВ.
        :raises ArgumentsException: Если данные не словарь, дата не в формате ``ГГГГ-ММ-ДД``,
            начало позже конца или условия фильтра некорректны.
        """
        fields = CommonValidator.validate_dict(data, "data")
        start = fields.get("start")
        end = fields.get("end")
        return cls(
            start=None if start is None else CommonValidator.validate_date(start, "start"),
            end=None if end is None else CommonValidator.validate_date(end, "end"),
            filter_dto=FilterDto.from_dict(fields),
        )

    @property
    def start(self) -> date | None:
        """Возвращает первый день периода, None — с первой записи."""
        return self._start

    @property
    def end(self) -> date | None:
        """Возвращает последний день периода, None — по сегодняшний день."""
        return self._end

    @property
    def filter(self) -> FilterDto:
        """Возвращает условия отбора записей журнала."""
        return self._filter
