from Src.Core.common_validator import CommonValidator
from Src.Models.nomenclature_model import NomenclatureModel


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
    - Веса не хранятся, а вычисляются при каждом обращении: изменение количества, потерь
      или веса базовой единицы номенклатуры сразу отражается в расчёте.
    - Способ приготовления не хранится: на расчёт влияет только явно заданная доля потерь,
      а описание обработки лежит в шагах технологической карты.
    """

    # Номенклатура ингредиента
    _nomenclature: NomenclatureModel
    # Количество в базовой единице номенклатуры (задаётся через сеттер, а не в __init__ напрямую)
    _quantity: int | float  # pyright: ignore[reportUninitializedInstanceVariable]
    # Доля потерь при приготовлении, от 0 включительно до 1 не включая (задаётся через сеттер)
    _loss_ratio: int | float  # pyright: ignore[reportUninitializedInstanceVariable]

    def __init__(self, nomenclature: NomenclatureModel, quantity: float, loss_ratio: float = 0) -> None:
        """Инициализирует ингредиент.

        :param nomenclature: Номенклатура ингредиента.
        :param quantity: Количество в базовой единице номенклатуры, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям.
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self.quantity = quantity
        self.loss_ratio = loss_ratio

    @property
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру ингредиента.

        Только для чтения: задаётся в конструкторе.
        """
        return self._nomenclature

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
        """Возвращает вес брутто в граммах: исходный вес до потерь при приготовлении."""
        return self._quantity * self._nomenclature.grams_per_base_unit

    @property
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес после потерь при приготовлении."""
        return self.gross_weight * (1 - self._loss_ratio)
