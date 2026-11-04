from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_model import NomenclatureModel


class IngredientDeserializer(AbstractDeserializer):
    """Десериализатор ингредиента — строки состава карты.

    Основание (``base``) — список таких же ингредиентов, поэтому десериализатор вызывает сам себя через
    рекурсию на любую глубину. У ингредиента нет идентификатора, в кэш он не попадает; номенклатура
    внутри него берётся из кэша, и все строки ссылаются на общие объекты.
    Вычисляемые поля ``gross_weight`` и ``net_weight`` игнорируются.
    """

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт ингредиент по полям ``nomenclature``, ``quantity``, ``loss_ratio`` и ``base``.

        Доля потерь и основание необязательны, как и параметры конструктора: по умолчанию 0 и пустое основание.

        :param data: Словарь полей ингредиента.
        :return: Новый ингредиент.
        :raises ArgumentsException: Если обязательные поля отсутствуют или некорректны.
        :raises OperationException: Если номенклатура — ссылка на модель, которой нет в данных.
        """
        return IngredientModel(
            nomenclature=self._nested(NomenclatureModel, CommonValidator.validate_field(data, "nomenclature")),
            quantity=cast(float, CommonValidator.validate_field(data, "quantity")),
            loss_ratio=cast(float, data.get("loss_ratio", 0)),
            # Рекурсия: каждая строка основания собирается этим же десериализатором
            base=self._nested_list(IngredientModel, data.get("base", []), "base"),
        )
