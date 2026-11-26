from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


class TurnoverRow:
    """Строка оборотно-сальдовой ведомости: движение одной номенклатуры по одному складу за период.

    Все количества — в базовой единице номенклатуры (``range``), уже пересчитанные из единиц записей журнала.
    Остаток на конец не хранится, а вычисляется: так он не может разойтись с остальными колонками.
    """

    # Номенклатура строки
    _nomenclature: NomenclatureModel
    # Склад строки
    _warehouse: WarehouseModel
    # Базовая единица номенклатуры, в которой записаны количества
    _range: RangeModel
    # Остаток на начало периода
    _opening: int | float
    # Приход за период
    _income: int | float
    # Расход за период, положительное число
    _outcome: int | float

    def __init__(
        self,
        nomenclature: NomenclatureModel,
        warehouse: WarehouseModel,
        range: RangeModel,
        opening: float,
        income: float,
        outcome: float,
    ) -> None:
        """Инициализирует строку ОСВ.

        :param nomenclature: Номенклатура.
        :param warehouse: Склад.
        :param range: Базовая единица номенклатуры.
        :param opening: Остаток на начало периода, может быть отрицательным (списание «под сальдо», п. 2.4 ТЗ).
        :param income: Приход за период, не меньше нуля.
        :param outcome: Расход за период, не меньше нуля: знак уже учтён названием колонки.
        :raises ArgumentsException: Если параметр не того типа, единица не базовая, количество не конечное число
            либо приход или расход отрицательны.
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self._warehouse = CommonValidator.validate_instance(warehouse, WarehouseModel, "warehouse", "Ожидается склад")
        self._range = CommonValidator.validate_instance(range, RangeModel, "range", "Ожидается единица измерения")
        if not self._range.is_base:
            raise ArgumentsException("range", f"Ожидается базовая единица измерения: {self._range.name}")
        self._opening = CommonValidator.validate_finite_number(opening, "opening")
        self._income = CommonValidator.validate_non_negative_number(income, "income")
        self._outcome = CommonValidator.validate_non_negative_number(outcome, "outcome")

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
        """Возвращает базовую единицу, в которой записаны количества."""
        return self._range

    @property
    def opening(self) -> int | float:
        """Возвращает остаток на начало периода."""
        return self._opening

    @property
    def income(self) -> int | float:
        """Возвращает приход за период."""
        return self._income

    @property
    def outcome(self) -> int | float:
        """Возвращает расход за период положительным числом."""
        return self._outcome

    @property
    def closing(self) -> int | float:
        """Возвращает остаток на конец периода: начало + приход − расход."""
        return self._opening + self._income - self._outcome
