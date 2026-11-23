from datetime import date

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException, OperationException
from Src.Dtos.turnover_row import TurnoverRow
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.transaction_model import TransactionModel
from Src.Models.warehouse_model import WarehouseModel


class TurnoverAccumulatorDto:
    """Аккумулятор показателей строки оборотно-сальдовой ведомости (ОСВ).

    Инкапсулирует накопление остатка на начало периода, прихода и расхода в базовой единице
    из проводок журнала складских операций. Заменяет сырые списки чисел и процедурные манипуляции.
    """

    # Номенклатура строки
    _nomenclature: NomenclatureModel
    # Склад строки
    _warehouse: WarehouseModel
    # Базовая единица номенклатуры, в которой ведутся итоги
    _range: RangeModel
    # Остаток на начало периода
    _opening: float
    # Приход за период
    _income: float
    # Расход за период (положительное число)
    _outcome: float

    def __init__(
        self,
        nomenclature: NomenclatureModel,
        warehouse: WarehouseModel,
        range: RangeModel,
        opening: float = 0.0,
        income: float = 0.0,
        outcome: float = 0.0,
    ) -> None:
        """Инициализирует аккумулятор строки ведомости.

        :param nomenclature: Номенклатура.
        :param warehouse: Склад.
        :param range: Базовая единица номенклатуры.
        :param opening: Начальный остаток на начало периода, по умолчанию 0.0.
        :param income: Начальный приход за период, по умолчанию 0.0.
        :param outcome: Начальный расход за период, по умолчанию 0.0.
        :raises ArgumentsException: Если передан параметр неверного типа, единица не базовая
            или значения не являются конечными неотрицательными числами (для прихода/расхода).
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self._warehouse = CommonValidator.validate_instance(warehouse, WarehouseModel, "warehouse", "Ожидается склад")
        self._range = CommonValidator.validate_instance(range, RangeModel, "range", "Ожидается единица измерения")
        if not self._range.is_base:
            raise ArgumentsException("range", f"Ожидается базовая единица измерения: {self._range.name}")
        self._opening = float(CommonValidator.validate_finite_number(opening, "opening"))
        self._income = float(CommonValidator.validate_non_negative_number(income, "income"))
        self._outcome = float(CommonValidator.validate_non_negative_number(outcome, "outcome"))

    @property
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру."""
        return self._nomenclature

    @property
    def warehouse(self) -> WarehouseModel:
        """Возвращает склад."""
        return self._warehouse

    @property
    def range(self) -> RangeModel:
        """Возвращает базовую единицу измерения."""
        return self._range

    @property
    def opening(self) -> float:
        """Возвращает накопленный остаток на начало периода."""
        return self._opening

    @property
    def income(self) -> float:
        """Возвращает накопленный приход за период."""
        return self._income

    @property
    def outcome(self) -> float:
        """Возвращает накопленный расход за период."""
        return self._outcome

    def record(self, transaction: TransactionModel, start: date) -> None:
        """Учитывает проводку журнала складских операций в накопленных итогах.

        Количество пересчитывается в базовую единицу номенклатуры: ``quantity × range.factor``.
        Записи с датой строго раньше ``start`` увеличивают остаток на начало.
        Записи периода (начиная с ``start``) увеличивают приход (положительные) или расход (отрицательные).

        :param transaction: Запись журнала складских операций.
        :param start: Первый день периода включительно.
        :raises OperationException: Если базовая единица записи не совпадает с базовой единицей строки.
        """
        if transaction.range.base is not self._range:
            raise OperationException(
                f"Единица записи {transaction.range.name} не приводится к базовой единице номенклатуры "
                + f"{self._nomenclature.name}: {self._range.name}"
            )

        quantity = transaction.quantity * transaction.range.factor
        day = transaction.period.date()
        if day < start:
            self._opening += quantity
        elif quantity > 0:
            self._income += quantity
        else:
            self._outcome += abs(quantity)

    def to_row(self) -> TurnoverRow:
        """Формирует неизменяемую строку ОСВ по накопленным показателям.

        :return: Строка ведомости с вычисленным остатком на конец периода.
        """
        return TurnoverRow(
            nomenclature=self._nomenclature,
            warehouse=self._warehouse,
            range=self._range,
            opening=self._opening,
            income=self._income,
            outcome=self._outcome,
        )
