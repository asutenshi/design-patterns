# pyright: reportImportCycles=false
# Цикл с recipe_model осознанный: фабрика create_borscht импортирует этот модуль локально, внутри метода,
# поэтому при загрузке модулей цикла нет. Статический анализ видит и локальные импорты.
from typing import override

from Src.Core.common_validator import CommonValidator
from Src.Models.abstract_recipe_item import AbstractRecipeItem
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.recipe_model import RecipeModel


class NestedRecipeModel(AbstractRecipeItem):
    """Модель вложенной карты: технологическая карта полуфабриката или блюда в составе другой карты (п. 2.5 ТЗ).

    Класс-ассоциация «карта + количество + потери»: одна и та же карта может входить в разные карты
    в разном количестве и с разными потерями, поэтому эти значения принадлежат связи, а не самой карте.
    Количество измеряется в базовой единице результата вложенной карты.

    Веса считаются рекурсивно (паттерн «Компоновщик») пропорционально доле выхода вложенной карты:
    ``recipe.gross_weight * quantity / recipe.output_quantity``. Потери строки применяются к весу нетто.

    Проектные решения:

    - Ссылка на вложенную карту живая и общая: копии и слепка нет, поэтому правка вложенной карты
      сразу меняет вес всех карт, в которые она входит. Веса не кешируются.
    - ``recipe`` задаётся только в конструкторе и не имеет сеттера: связь между картами создаётся
      лишь при добавлении элемента в карту, где ``RecipeModel.add_item`` проверяет циклы. Сеттер позволил бы
      замкнуть цикл у уже добавленного элемента в обход проверки.
    - Номенклатура элемента — результат вложенной карты, отдельно она не хранится и не может разойтись с картой.
    - Хранилище не следит за использованием карты: если карту заменить или удалить в хранилище,
      карты, в которые она входила, сохранят прежнюю. Запрет удаления используемой карты — задача слоя Logics.
    """

    # Вложенная технологическая карта полуфабриката или блюда
    _recipe: RecipeModel

    def __init__(self, recipe: RecipeModel, quantity: float, loss_ratio: float = 0) -> None:
        """Инициализирует вложенную карту.

        :param recipe: Технологическая карта полуфабриката или блюда.
        :param quantity: Количество в базовой единице результата карты, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям.
        """
        super().__init__(quantity, loss_ratio)
        self._recipe = CommonValidator.validate_instance(
            recipe, RecipeModel, "recipe", "Ожидается технологическая карта"
        )

    @property
    def recipe(self) -> RecipeModel:
        """Возвращает вложенную технологическую карту.

        Только для чтения: задаётся в конструкторе.
        """
        return self._recipe

    @property
    @override
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру элемента: результат вложенной карты."""
        return self._recipe.result

    @property
    @override
    def gross_weight(self) -> float:
        """Возвращает вес брутто в граммах: вес брутто вложенной карты пропорционально количеству в строке."""
        ratio = self._quantity / self._recipe.output_quantity
        return self._recipe.gross_weight * ratio

    @property
    @override
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес нетто вложенной карты пропорционально количеству и с учётом потерь."""
        ratio = self._quantity / self._recipe.output_quantity
        return self._recipe.net_weight * ratio * (1 - self._loss_ratio)

    @override
    def depends_on(self, nomenclature: NomenclatureModel) -> bool:
        """Проверяет, входит ли номенклатура в вложенную карту: как её результат или через её состав.

        :param nomenclature: Искомая номенклатура.
        :return: True, если номенклатура совпадает с результатом вложенной карты или есть в её составе.
        """
        return self._recipe.result == nomenclature or any(item.depends_on(nomenclature) for item in self._recipe.items)
