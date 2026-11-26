from datetime import date

from Src.Dtos.turnover_accumulator_dto import TurnoverAccumulatorDto
from Src.Dtos.turnover_group_key_dto import TurnoverGroupKeyDto
from Src.Dtos.turnover_report import TurnoverReport
from Src.Dtos.turnover_request_dto import TurnoverRequestDto
from Src.Dtos.turnover_row import TurnoverRow
from Src.Logics.prototype import Prototype
from Src.Logics.storage_manager import StorageManager
from Src.Models.transaction_model import TransactionModel


class TurnoverService:
    """Сервис оборотно-сальдовой ведомости (ОСВ) по журналу складских операций.

    Записи журнала отбирает Прототип по условиям запроса, а период сервис применяет сам:
    записи до начала периода не отбрасываются, а дают остаток на начало. Поэтому Прототип
    ничего не знает о смысле дат, а сервис — о том, как устроен фильтр.
    """

    # Хранилище с журналом складских операций
    _storage: StorageManager

    def __init__(self, storage: StorageManager | None = None) -> None:
        """Создаёт сервис поверх хранилища.

        :param storage: Хранилище, с которым работает сервис; None — единственный экземпляр StorageManager.
        """
        self._storage = StorageManager() if storage is None else storage

    def build(self, request: TurnoverRequestDto) -> TurnoverReport:
        """Строит ОСВ по запросу.

        Записи журнала отбирает ``Prototype`` по условиям запроса. Отсутствующие границы периода
        подставляются так: конец — сегодняшний день, начало — дата первой отобранной записи
        (но не позже конца), чтобы остаток на начало был нулевым.

        :param request: Период и условия отбора.
        :return: ОСВ с вычисленными границами периода.
        :raises ArgumentsException: Если условие фильтра ведёт к недоступному полю.
        :raises OperationException: Если в одной строке встретились записи с разными базовыми единицами.
        """
        transactions = Prototype(self._storage.transactions).clone(request.filter).data
        end = date.today() if request.end is None else request.end
        start = request.start
        if start is None:
            start = min([item.period.date() for item in transactions] + [end])
        return TurnoverReport(start, end, self._calculate_rows(transactions, start, end))

    def _calculate_rows(self, transactions: list[TransactionModel], start: date, end: date) -> list[TurnoverRow]:
        """Считает строки ОСВ по отобранным записям журнала.

        - Записи группируются по паре «номенклатура + склад» с помощью типизированного ключа ``TurnoverGroupKeyDto``.
          Строки идут в порядке первого появления группы в журнале.
        - Итоги каждой группы накапливает объект ``TurnoverAccumulatorDto``: остаток на начало, приход и расход.
        - Записи после ``end`` не учитываются совсем: если у группы других записей нет, строка не создаётся.
        - Количество записи пересчитывается в базовую единицу: ``quantity × range.factor``.
        - Записи строго до ``start`` дают остаток на начало, записи с ``start`` по ``end`` включительно —
          приход (положительные) и расход (отрицательные, в колонку пишется модуль).
          Сравнивается дата записи (``period.date()``), время не важно.

        :param transactions: Отобранные записи журнала в порядке проведения.
        :param start: Первый день периода включительно.
        :param end: Последний день периода включительно.
        :return: Строки ОСВ.
        :raises OperationException: Если базовая единица записи не совпадает с базовой единицей номенклатуры
            (единицу номенклатуры сменили после проведения записи).
        """
        accumulators: dict[TurnoverGroupKeyDto, TurnoverAccumulatorDto] = {}

        for transaction in transactions:
            if transaction.period.date() > end:
                continue

            nomenclature = transaction.nomenclature
            key = TurnoverGroupKeyDto(nomenclature, transaction.warehouse)
            if key not in accumulators:
                accumulators[key] = TurnoverAccumulatorDto(
                    nomenclature=nomenclature,
                    warehouse=transaction.warehouse,
                    range=nomenclature.range.base,
                )

            accumulators[key].record(transaction, start)

        return [accumulator.to_row() for accumulator in accumulators.values()]
