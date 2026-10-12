import uuid
from typing import Protocol, runtime_checkable

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_model import NomenclatureModel


@runtime_checkable
class RecipeProtocol(Protocol):
    """Протокол технологической карты для рекурсивного расчёта весов (паттерн «Компоновщик»)."""

    @property
    def id(self) -> uuid.UUID:
        """Идентификатор карты."""
        ...

    @property
    def result(self) -> NomenclatureModel:
        """Номенклатура-результат карты."""
        ...

    @property
    def output_quantity(self) -> int | float:
        """Выход в базовой единице результата."""
        ...

    @property
    def gross_weight(self) -> float:
        """Вес брутто карты в граммах."""
        ...

    @property
    def net_weight(self) -> float:
        """Вес нетто карты в граммах."""
        ...

    @property
    def ingredients(self) -> list["IngredientModel"]:
        """Список ингредиентов карты."""
        ...


class IngredientModel:
    """Модель строки состава технологической карты: номенклатура, количество и потери.

    Количество измеряется в базовой единице номенклатуры (``nomenclature.range.base``):
    если номенклатура учитывается в килограммах, то ``800`` означает 800 г.
    Вес в граммах вычисляется из количества и ``nomenclature.grams_per_base_unit``.

    Проектные решения:

    - Ингредиент принадлежит одной карте и не переиспользуется, поэтому он не наследует
      BaseEntity: собственный id ему не нужен, внутри карты его определяет номенклатура.
    - ``nomenclature`` задаётся только в конструкторе и не имеет сеттера: она служит ключом
      уникальности в коллекции карты, и смена номенклатуры сделала бы ключ устаревшим.
    - ``recipe`` — опциональная технологическая карта полуфабриката или блюда (паттерн «Компоновщик»).
      Если она задана, веса рассчитываются рекурсивно через выход вложенной карты.
      Задаётся только в конструкторе и не имеет сеттера: связь между картами создаётся лишь при добавлении
      ингредиента в карту, где ``RecipeModel.add_ingredient`` проверяет циклы. Сеттер позволил бы замкнуть
      цикл у уже добавленного ингредиента в обход проверки, и расчёт веса ушёл бы в бесконечную рекурсию.
    - Веса не хранятся, а вычисляются при каждом обращении: изменение количества, потерь,
      вложенной карты или веса базовой единицы сразу отражается в расчёте.
    - Способ приготовления не хранится: на расчёт влияет только явно заданная доля потерь,
      а описание обработки лежит в шагах технологической карты.
    """

    # Номенклатура ингредиента
    _nomenclature: NomenclatureModel
    # Количество в базовой единице номенклатуры (задаётся через сеттер, а не в __init__ напрямую)
    _quantity: int | float  # pyright: ignore[reportUninitializedInstanceVariable]
    # Доля потерь при приготовлении, от 0 включительно до 1 не включая (задаётся через сеттер)
    _loss_ratio: int | float  # pyright: ignore[reportUninitializedInstanceVariable]
    # Технологическая карта приготовления полуфабриката или блюда, если задана
    _recipe: RecipeProtocol | None

    def __init__(
        self,
        nomenclature: NomenclatureModel,
        quantity: float,
        loss_ratio: float = 0,
        recipe: RecipeProtocol | None = None,
    ) -> None:
        """Инициализирует ингредиент.

        :param nomenclature: Номенклатура ингредиента.
        :param quantity: Количество в базовой единице номенклатуры, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :param recipe: Технологическая карта приготовления полуфабриката или блюда,
            если номенклатура является результатом другой карты. По умолчанию None.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям
            или результат карты не совпадает с номенклатурой ингредиента.
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self.quantity = quantity
        self.loss_ratio = loss_ratio
        if recipe is not None:
            recipe = CommonValidator.validate_instance(
                recipe, RecipeProtocol, "recipe", "Ожидается технологическая карта"
            )
            if recipe.result != self._nomenclature:
                raise ArgumentsException("recipe", "Результат карты должен совпадать с номенклатурой ингредиента")
        self._recipe = recipe

    @property
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру ингредиента.

        Только для чтения: задаётся в конструкторе.
        """
        return self._nomenclature

    @property
    def recipe(self) -> RecipeProtocol | None:
        """Возвращает технологическую карту полуфабриката или блюда, если она задана.

        Только для чтения: задаётся в конструкторе.
        """
        return self._recipe

    def nomenclature_key(self) -> uuid.UUID:
        """Возвращает ключ уникальности ингредиента в карте: идентификатор его номенклатуры.

        Передаётся как функция ключа в UniqueCollection: ``UniqueCollection(IngredientModel.nomenclature_key)``.
        """
        return self._nomenclature.id

    @property
    def quantity(self) -> int | float:
        """Возвращает количество в базовой единице номенклатуры."""
        return self._quantity

    @quantity.setter
    def quantity(self, value: float) -> None:
        """Устанавливает количество в базовой единице номенклатуры.

        :param value: Новое количество, конечное число больше нуля.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        self._quantity = CommonValidator.validate_positive_number(value, "quantity")

    @property
    def loss_ratio(self) -> int | float:
        """Возвращает долю потерь при приготовлении."""
        return self._loss_ratio

    @loss_ratio.setter
    def loss_ratio(self, value: float) -> None:
        """Устанавливает долю потерь при приготовлении.

        :param value: Новая доля потерь, число от 0 включительно до 1 не включая.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не лежит в промежутке [0, 1).
        """
        self._loss_ratio = CommonValidator.validate_fraction(value, "loss_ratio")

    @property
    def gross_weight(self) -> float:
        """Возвращает вес брутто в граммах: исходный вес до потерь при приготовлении.

        Если к ингредиенту привязана технологическая карта, вес брутто вычисляется
        рекурсивно по ней пропорционально количеству в строке (паттерн «Компоновщик»).
        Иначе вычисляется из количества и веса базовой единицы номенклатуры.
        """
        if self._recipe is not None:
            ratio = self._quantity / self._recipe.output_quantity
            return self._recipe.gross_weight * ratio
        return self._quantity * self._nomenclature.grams_per_base_unit

    @property
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес после потерь при приготовлении.

        Если к ингредиенту привязана технологическая карта, вес нетто вычисляется
        рекурсивно по ней пропорционально количеству в строке с учётом потерь этой строки.
        Иначе вычисляется из собственного веса брутто и доли потерь.
        """
        if self._recipe is not None:
            ratio = self._quantity / self._recipe.output_quantity
            return self._recipe.net_weight * ratio * (1 - self._loss_ratio)
        return self.gross_weight * (1 - self._loss_ratio)
