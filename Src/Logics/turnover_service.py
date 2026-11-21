import uuid
from datetime import date

from Src.Core.exception import OperationException
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

        - Записи группируются по паре «номенклатура + склад». Строки идут в порядке первой записи группы в журнале.
        - Записи после ``end`` не учитываются совсем: если у группы других записей нет, строки нет.
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
        # Первая запись группы: из неё берутся номенклатура и склад строки, порядок ключей — порядок строк
        first_records: dict[tuple[uuid.UUID, uuid.UUID], TransactionModel] = {}
        # Накопленные колонки группы: остаток на начало, приход, расход
        totals: dict[tuple[uuid.UUID, uuid.UUID], list[float]] = {}

        for transaction in transactions:
            day = transaction.period.date()
            if day > end:
                continue

            nomenclature = transaction.nomenclature
            if transaction.range.base is not nomenclature.range.base:
                raise OperationException(
                    f"Единица записи {transaction.range.name} не приводится к базовой единице номенклатуры "
                    + f"{nomenclature.name}: {nomenclature.range.base.name}"
                )

            key = (nomenclature.id, transaction.warehouse.id)
            if key not in totals:
                first_records[key] = transaction
                totals[key] = [0, 0, 0]

            quantity = transaction.quantity * transaction.range.factor
            if day < start:
                totals[key][0] += quantity
            elif quantity > 0:
                totals[key][1] += quantity
            else:
                totals[key][2] += abs(quantity)

        return [
            TurnoverRow(
                nomenclature=record.nomenclature,
                warehouse=record.warehouse,
                range=record.nomenclature.range.base,
                opening=totals[key][0],
                income=totals[key][1],
                outcome=totals[key][2],
            )
            for key, record in first_records.items()
        ]
