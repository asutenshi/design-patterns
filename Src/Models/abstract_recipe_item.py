import uuid
from abc import ABC, abstractmethod

from Src.Core.common_validator import CommonValidator
from Src.Models.nomenclature_model import NomenclatureModel


class AbstractRecipeItem(ABC):
    """Абстрактный элемент состава технологической карты: номенклатура, количество и потери.

    Общий интерфейс листа (``IngredientModel``: сырьё, упаковка) и вложенной карты
    (``NestedRecipeModel``) — паттерн «Компоновщик». Карта считает свой вес, не различая виды
    элементов: каждый элемент сам знает, как получить брутто и нетто.

    Количество измеряется в базовой единице номенклатуры элемента (``nomenclature.range.base``).

    Проектные решения:

    - Количество и доля потерь есть у любого элемента состава, поэтому их хранение и проверка
      лежат здесь, а не дублируются в наследниках.
    - Ключ уникальности элемента в карте — идентификатор его номенклатуры (``nomenclature_key``).
    - Элемент принадлежит одной карте и не наследует BaseEntity: собственный id ему не нужен.
    - Веса не хранятся, а вычисляются при каждом обращении: изменение количества, потерь
      или вложенной карты сразу отражается в расчёте.
    """

    # Количество в базовой единице номенклатуры (задаётся через сеттер, а не в __init__ напрямую)
    _quantity: int | float
    # Доля потерь при приготовлении, от 0 включительно до 1 не включая (задаётся через сеттер)
    _loss_ratio: int | float

    def __init__(self, quantity: float, loss_ratio: float = 0) -> None:
        """Инициализирует элемент состава.

        :param quantity: Количество в базовой единице номенклатуры, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :raises ArgumentsException: Если количество или доля потерь не соответствуют требованиям.
        """
        self.quantity = quantity
        self.loss_ratio = loss_ratio

    @property
    @abstractmethod
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру элемента.

        Только для чтения: служит ключом уникальности в карте, и её смена сделала бы ключ устаревшим.
        """

    @property
    @abstractmethod
    def gross_weight(self) -> float:
        """Возвращает вес брутто в граммах: исходный вес до потерь при приготовлении."""

    @property
    @abstractmethod
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес после потерь при приготовлении."""

    @abstractmethod
    def depends_on(self, nomenclature: NomenclatureModel) -> bool:
        """Проверяет, входит ли номенклатура в элемент: напрямую или через вложенные карты.

        Нужна карте для защиты от циклов: результат карты не должен входить в её собственный состав.

        :param nomenclature: Искомая номенклатура.
        :return: True, если номенклатура элемента совпадает с искомой или она есть во вложенных картах.
        """

    def nomenclature_key(self) -> uuid.UUID:
        """Возвращает ключ уникальности элемента в карте: идентификатор его номенклатуры.

        Передаётся как функция ключа в UniqueCollection: ``UniqueCollection(AbstractRecipeItem.nomenclature_key)``.
        """
        return self.nomenclature.id

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
