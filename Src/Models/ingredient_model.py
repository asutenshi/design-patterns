from typing import override

from Src.Core.common_validator import CommonValidator
from Src.Models.abstract_recipe_item import AbstractRecipeItem
from Src.Models.nomenclature_model import NomenclatureModel


class IngredientModel(AbstractRecipeItem):
    """Модель ингредиента: плоская строка состава технологической карты (сырьё, упаковка).

    Количество измеряется в базовой единице номенклатуры (``nomenclature.range.base``):
    если номенклатура учитывается в килограммах, то ``800`` означает 800 г.
    Вес в граммах вычисляется из количества и ``nomenclature.grams_per_base_unit``.
    Полуфабрикат или блюдо, у которого есть своя карта, входит в состав как ``NestedRecipeModel``.

    Проектные решения:

    - Ингредиент не знает о технологических картах: связь «номенклатура — карта» не нужна листу,
      а ссылка на карту из ингредиента замыкала бы зависимость карты и ингредиента друг на друга.
    - ``nomenclature`` задаётся только в конструкторе и не имеет сеттера: она служит ключом
      уникальности в коллекции карты, и смена номенклатуры сделала бы ключ устаревшим.
    - Способ приготовления не хранится: на расчёт влияет только явно заданная доля потерь,
      а описание обработки лежит в шагах технологической карты.
    """

    # Номенклатура ингредиента
    _nomenclature: NomenclatureModel

    def __init__(self, nomenclature: NomenclatureModel, quantity: float, loss_ratio: float = 0) -> None:
        """Инициализирует ингредиент.

        :param nomenclature: Номенклатура ингредиента.
        :param quantity: Количество в базовой единице номенклатуры, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям.
        """
        super().__init__(quantity, loss_ratio)
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )

    @property
    @override
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру ингредиента.

        Только для чтения: задаётся в конструкторе.
        """
        return self._nomenclature

    @property
    @override
    def gross_weight(self) -> float:
        """Возвращает вес брутто в граммах: количество, умноженное на вес базовой единицы номенклатуры."""
        return self._quantity * self._nomenclature.grams_per_base_unit

    @property
    @override
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес брутто за вычетом доли потерь."""
        return self.gross_weight * (1 - self._loss_ratio)

    @override
    def depends_on(self, nomenclature: NomenclatureModel) -> bool:
        """Проверяет, совпадает ли номенклатура ингредиента с искомой.

        :param nomenclature: Искомая номенклатура.
        :return: True, если номенклатура ингредиента совпадает с искомой.
        """
        return self._nomenclature == nomenclature
