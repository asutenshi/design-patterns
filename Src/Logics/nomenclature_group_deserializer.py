from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Models.nomenclature_group_model import NomenclatureGroupModel


class NomenclatureGroupDeserializer(AbstractDeserializer):
    """Десериализатор группы номенклатуры: у группы только наименование."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт группу номенклатуры по полю ``name``.

        :param data: Словарь полей группы.
        :return: Новая группа номенклатуры.
        :raises ArgumentsException: Если наименования нет или оно некорректно.
        """
        return NomenclatureGroupModel(cast(str, CommonValidator.validate_field(data, "name")))
