from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Models.warehouse_model import WarehouseModel


class WarehouseDeserializer(AbstractDeserializer):
    """Десериализатор склада: у склада только наименование."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт склад по полю ``name``.

        :param data: Словарь полей склада.
        :return: Новый склад.
        :raises ArgumentsException: Если наименования нет или оно некорректно.
        """
        return WarehouseModel(cast(str, CommonValidator.validate_field(data, "name")))
