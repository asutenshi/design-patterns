from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel


class NomenclatureDeserializer(AbstractDeserializer):
    """Десериализатор номенклатуры: группа и единица измерения собираются рекурсивно, тип — из значения перечисления."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт номенклатуру по полям ``name``, ``full_name``, ``group``, ``range``, ``type``, ``grams_per_base_unit``.

        :param data: Словарь полей номенклатуры.
        :return: Новая номенклатура.
        :raises ArgumentsException: Если поля отсутствуют или некорректны, тип неизвестен перечислению.
        :raises OperationException: Если группа или единица — ссылка на модель, которой нет в данных.
        """
        return NomenclatureModel(
            name=cast(str, CommonValidator.validate_field(data, "name")),
            full_name=cast(str, CommonValidator.validate_field(data, "full_name")),
            group=self._nested(NomenclatureGroupModel, CommonValidator.validate_field(data, "group")),
            range=self._nested(RangeModel, CommonValidator.validate_field(data, "range")),
            type=CommonValidator.validate_enum(CommonValidator.validate_field(data, "type"), NomenclatureType, "type"),
            grams_per_base_unit=cast(float, CommonValidator.validate_field(data, "grams_per_base_unit")),
        )
