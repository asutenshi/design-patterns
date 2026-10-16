import uuid
from collections.abc import Iterable
from typing import cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.unique_collection import UniqueCollection
from Src.Models.nomenclature_model import NomenclatureModel


class IngredientModel:
    """Модель ингредиента: строка состава технологической карты с основанием (паттерн «Компоновщик»).

    Количество измеряется в базовой единице номенклатуры (``nomenclature.range.base``):
    если номенклатура учитывается в килограммах, то ``800`` означает 800 г.

    Основание (``base``) — состав именно этого количества ингредиента. Пустое основание — сырьё
    или упаковка: вес вычисляется из количества и ``nomenclature.grams_per_base_unit``. Непустое —
    полуфабрикат или блюдо со своей картой (п. 2.5 ТЗ): вес — сумма весов основания, рекурсивно.
    Так лист и составной узел — один класс, и карте не нужно различать виды строк.

    Проектные решения:

    - Основание — производные данные, источник истины — карта полуфабриката, которую можно найти
      по номенклатуре ингредиента (``StorageManager.find_recipe``). Строку собирает
      ``RecipeModel.as_ingredient``, масштабируя состав карты под количество строки. Правка карты
      полуфабриката уже собранную строку не меняет: каскадную пересборку строк в картах,
      куда полуфабрикат входит, в будущем возьмёт на себя наблюдатель (паттерн «Наблюдатель»).
      В БД основание хранить не нужно, его пересобирают из карты при загрузке.
    - Основание задаётся только в конструкторе и копируется, наружу отдаются копии. Узел включает
      лишь узлы, созданные раньше него, поэтому циклы невозможны по построению.
    - Номенклатура узла не может встречаться в его основании: полуфабрикат не состоит из самого себя.
    - Смена количества составного узла пропорционально масштабирует основание: оно всегда
      описывает текущее количество.
    - Ингредиент не знает о технологических картах: фабрика строки лежит в ``RecipeModel``,
      иначе модули карты и ингредиента импортировали бы друг друга.
    - ``nomenclature`` задаётся только в конструкторе и не имеет сеттера: она служит ключом
      уникальности в коллекции карты, и смена номенклатуры сделала бы ключ устаревшим.
    - Ингредиент принадлежит одной карте и не наследует BaseEntity: собственный id ему не нужен.
    - Веса не хранятся, а вычисляются при каждом обращении: изменение количества или потерь
      сразу отражается в расчёте.
    - Способ приготовления не хранится: на расчёт влияет только явно заданная доля потерь,
      а описание обработки лежит в шагах технологической карты.
    """

    # Номенклатура ингредиента
    _nomenclature: NomenclatureModel
    # Количество в базовой единице номенклатуры
    _quantity: int | float
    # Доля потерь при приготовлении, от 0 включительно до 1 не включая
    _loss_ratio: int | float
    # Основание: состав этого количества ингредиента, пусто у сырья
    _base: tuple["IngredientModel", ...]

    def __init__(
        self,
        nomenclature: NomenclatureModel,
        quantity: float,
        loss_ratio: float = 0,
        base: Iterable["IngredientModel"] = (),
    ) -> None:
        """Инициализирует ингредиент.

        :param nomenclature: Номенклатура ингредиента.
        :param quantity: Количество в базовой единице номенклатуры, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении, от 0 включительно до 1 не включая.
            По умолчанию 0: потерь нет.
        :param base: Основание — состав указанного количества ингредиента. Элементы копируются.
            По умолчанию пусто: сырьё или упаковка.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям,
            в основании повторяется номенклатура или встречается номенклатура самого ингредиента.
        """
        self._nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        # Сеттеры здесь не вызываются: сеттер количества масштабирует основание, которого ещё нет
        self._quantity = CommonValidator.validate_positive_number(quantity, "quantity")
        self._loss_ratio = CommonValidator.validate_fraction(loss_ratio, "loss_ratio")
        self._base = self._copy_base(base)

    def _copy_base(self, base: Iterable["IngredientModel"]) -> tuple["IngredientModel", ...]:
        """Проверяет основание и возвращает копии его элементов.

        :param base: Основание ингредиента.
        :return: Копии элементов основания в исходном порядке.
        :raises ArgumentsException: Если основание содержит не ингредиент, повторяющуюся номенклатуру
            или номенклатуру самого ингредиента.
        """
        unique = UniqueCollection(IngredientModel.nomenclature_key)
        for element in cast(Iterable[object], base):
            ingredient = CommonValidator.validate_instance(element, IngredientModel, "base", "Ожидается ингредиент")
            if ingredient.contains(self._nomenclature):
                raise ArgumentsException("base", "Номенклатура ингредиента не может входить в его основание")
            unique.add(ingredient)

        return tuple(ingredient.scaled(1) for ingredient in unique)

    @property
    def nomenclature(self) -> NomenclatureModel:
        """Возвращает номенклатуру ингредиента.

        Только для чтения: задаётся в конструкторе.
        """
        return self._nomenclature

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

        Основание составного узла масштабируется пропорционально новому количеству.

        :param value: Новое количество, конечное число больше нуля.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        value = CommonValidator.validate_positive_number(value, "quantity")
        if self._base:
            factor = value / self._quantity
            self._base = tuple(ingredient.scaled(factor) for ingredient in self._base)
        self._quantity = value

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
    def base(self) -> tuple["IngredientModel", ...]:
        """Возвращает копию основания: изменить состав узла в обход количества нельзя.

        Только для чтения: задаётся в конструкторе.
        """
        return tuple(ingredient.scaled(1) for ingredient in self._base)

    @property
    def gross_weight(self) -> float:
        """Возвращает вес брутто в граммах: исходный вес до потерь при приготовлении.

        У сырья — количество, умноженное на вес базовой единицы номенклатуры,
        у составного узла — сумма брутто основания.
        """
        if not self._base:
            return self._quantity * self._nomenclature.grams_per_base_unit
        return sum((ingredient.gross_weight for ingredient in self._base), 0.0)

    @property
    def net_weight(self) -> float:
        """Возвращает вес нетто в граммах: вес после потерь при приготовлении.

        У сырья — вес брутто за вычетом доли потерь, у составного узла — сумма нетто основания
        за вычетом доли потерь самого узла.
        """
        if not self._base:
            return self.gross_weight * (1 - self._loss_ratio)
        return sum((ingredient.net_weight for ingredient in self._base), 0.0) * (1 - self._loss_ratio)

    def scaled(self, factor: float) -> "IngredientModel":
        """Возвращает копию ингредиента с количеством, умноженным на коэффициент.

        Основание масштабируется рекурсивно, доля потерь не меняется. ``scaled(1)`` — глубокая копия.

        :param factor: Коэффициент масштабирования, число больше нуля.
        :return: Новый ингредиент.
        :raises ArgumentsException: Если коэффициент не число (в том числе bool),
            не конечное или не больше нуля.
        """
        factor = CommonValidator.validate_positive_number(factor, "factor")
        copy = IngredientModel(self._nomenclature, self._quantity * factor, self._loss_ratio)
        # Основание копируется напрямую: проверки уже пройдены, а конструктор скопировал бы его повторно
        copy._base = tuple(ingredient.scaled(factor) for ingredient in self._base)
        return copy

    def contains(self, nomenclature: NomenclatureModel) -> bool:
        """Проверяет, есть ли номенклатура в узле: как его номенклатура или в основании на любой глубине.

        Нужна карте для защиты от включения снимка самой себя.

        :param nomenclature: Искомая номенклатура.
        :return: True, если номенклатура совпадает с номенклатурой узла или есть в его основании.
        """
        return self._nomenclature == nomenclature or any(ingredient.contains(nomenclature) for ingredient in self._base)
