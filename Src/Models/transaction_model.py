from datetime import datetime
from typing import Self, cast, override

from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


class TransactionModel(BaseEntity):
    """Модель записи журнала складских операций: движение номенклатуры по складу.

    Знак количества различает операции: плюс — приход, минус — расход, ноль запрещён.
    Количество записывается в той единице, что в первичном документе (например, «2 т»),
    а пересчёт в базовую единицу номенклатуры выполняет тот, кто считает остатки.

    Проектные решения:

    - Наименования у записи нет, поэтому модель наследует BaseEntity, а не NamedEntity.
    - Все поля задаются только в конструкторе и не имеют сеттеров: по Docs/DomainEntities.md
      запись журнала после проведения не меняется.
    - Единица записи должна приводиться к той же базовой единице, что и единица номенклатуры
      (``range.base is nomenclature.range.base``): иначе говядину можно было бы оприходовать в литрах.
      Единицу номенклатуры могут сменить позже, поэтому отчёты по журналу проверяют базу ещё раз.
    """

    # Номенклатура, которая движется по складу
    _nomenclature: NomenclatureModel
    # Склад, на котором прошла операция
    _warehouse: WarehouseModel
    # Единица измерения количества
    _range: RangeModel
    # Количество со знаком: плюс — приход, минус — расход
    _quantity: int | float
    # Дата и время операции
    _period: datetime

    def __init__(
        self,
        nomenclature: NomenclatureModel,
        warehouse: WarehouseModel,
        range: RangeModel,
        quantity: float,
        period: datetime,
    ) -> None:
        """Инициализирует запись журнала.

        :param nomenclature: Номенклатура.
        :param warehouse: Склад.
        :param range: Единица измерения количества с той же базовой единицей, что у номенклатуры.
        :param quantity: Количество со знаком: плюс — приход, минус — расход. Не ноль.
        :param period: Дата и время операции.
        :raises ArgumentsException: Если параметр не того типа, количество не конечное число или ноль
            либо базовая единица записи не совпадает с базовой единицей номенклатуры.
        """
        super().__init__()
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self._warehouse = CommonValidator.validate_instance(warehouse, WarehouseModel, "warehouse", "Ожидается склад")
        self._range = CommonValidator.validate_instance(range, RangeModel, "range", "Ожидается единица измерения")
        if self._range.base is not self._nomenclature.range.base:
            raise ArgumentsException(
                "range",
                f"Единица {self._range.name} не приводится к базовой единице номенклатуры "
                + f"{self._nomenclature.name}: {self._nomenclature.range.base.name}",
            )
        self._quantity = CommonValidator.validate_nonzero_number(quantity, "quantity")
        self._period = CommonValidator.validate_instance(period, datetime, "period", "Ожидается дата и время")

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт запись по полям ``nomenclature``, ``warehouse``, ``range``, ``quantity``
        и ``period``.

        Дата записана в JSON строкой ISO 8601 и превращается в ``datetime``.

        :param data: Поля записи, номенклатура, склад и единица уже собраны.
        :return: Новая запись журнала.
        :raises ArgumentsException: Если обязательного поля нет, дата не в формате ISO 8601
            или значение не проходит проверку конструктора.
        """
        return cls(
            nomenclature=cast(NomenclatureModel, CommonValidator.validate_field(data, "nomenclature")),
            warehouse=cast(WarehouseModel, CommonValidator.validate_field(data, "warehouse")),
            range=cast(RangeModel, CommonValidator.validate_field(data, "range")),
            quantity=cast(float, CommonValidator.validate_field(data, "quantity")),
            period=CommonValidator.validate_datetime(CommonValidator.validate_field(data, "period"), "period"),
        )

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
        """Возвращает единицу измерения количества."""
        return self._range

    @property
    def quantity(self) -> int | float:
        """Возвращает количество со знаком: плюс — приход, минус — расход."""
        return self._quantity

    @property
    def period(self) -> datetime:
        """Возвращает дату и время операции."""
        return self._period

    @override
    def references(self) -> list[BaseEntity]:
        """Возвращает номенклатуру, склад и единицу измерения записи.

        :return: Сущности, на которые ссылается запись.
        """
        return [self._nomenclature, self._warehouse, self._range]
