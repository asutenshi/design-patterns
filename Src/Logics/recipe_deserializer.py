from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.recipe_model import RecipeModel


class RecipeDeserializer(AbstractDeserializer):
    """Десериализатор технологической карты: результат и ингредиенты собираются рекурсивно.

    Основание составных ингредиентов берётся из данных как есть, а не пересобирается из карт полуфабрикатов:
    в файле оно уже записано. Вычисляемые поля ``gross_weight`` и ``net_weight`` игнорируются.
    """

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт карту по полям ``name``, ``result``, ``output_quantity``, ``cooking_time_minutes``, ``steps``, ``items``.

        :param data: Словарь полей карты.
        :return: Новая технологическая карта.
        :raises ArgumentsException: Если поля отсутствуют или некорректны.
        :raises OperationException: Если результат или номенклатура ингредиента — ссылка на модель,
            которой нет в данных.
        """
        return RecipeModel(
            name=cast(str, CommonValidator.validate_field(data, "name")),
            result=self._nested(NomenclatureModel, CommonValidator.validate_field(data, "result")),
            output_quantity=cast(float, CommonValidator.validate_field(data, "output_quantity")),
            cooking_time_minutes=cast(float, CommonValidator.validate_field(data, "cooking_time_minutes")),
            steps=cast(list[str], CommonValidator.validate_field(data, "steps")),
            items=self._nested_list(IngredientModel, CommonValidator.validate_field(data, "items"), "items"),
        )
