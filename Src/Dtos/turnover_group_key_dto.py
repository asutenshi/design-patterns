from typing import override

from Src.Core.common_validator import CommonValidator
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.warehouse_model import WarehouseModel


class TurnoverGroupKeyDto:
    """Ключ группировки строк оборотно-сальдовой ведомости: пара «номенклатура + склад».

    Используется как типизированный ключ группировки записей журнала вместо кортежей и сырых данных.
    Равенство и хэш определяются уникальными идентификаторами сущностей.
    """

    # Номенклатура группы
    _nomenclature: NomenclatureModel
    # Склад группы
    _warehouse: WarehouseModel

    def __init__(self, nomenclature: NomenclatureModel, warehouse: WarehouseModel) -> None:
        """Инициализирует ключ группировки.

        :param nomenclature: Номенклатура.
        :param warehouse: Склад.
        :raises ArgumentsException: Если параметры не соответствуют ожидаемым типам сущностей.
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self._warehouse = CommonValidator.validate_instance(warehouse, WarehouseModel, "warehouse", "Ожидается склад")

    @property
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру группы."""
        return self._nomenclature

    @property
    def warehouse(self) -> WarehouseModel:
        """Возвращает склад группы."""
        return self._warehouse

    @override
    def __eq__(self, other: object) -> bool:
        """Сравнивает ключи группировки по идентификаторам номенклатуры и склада."""
        if not isinstance(other, TurnoverGroupKeyDto):
            return False
        return self._nomenclature.id == other._nomenclature.id and self._warehouse.id == other._warehouse.id

    @override
    def __hash__(self) -> int:
        """Вычисляет хэш по паре кодов номенклатуры и склада."""
        return hash((self._nomenclature.id, self._warehouse.id))
