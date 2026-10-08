import uuid
from collections.abc import Iterable
from typing import ClassVar, cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.named_entity import NamedEntity
from Src.Core.nomenclature_type import NomenclatureType
from Src.Core.unique_collection import UniqueCollection
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_model import NomenclatureModel


def _nomenclature_key(nomenclature: NomenclatureModel) -> uuid.UUID:
    """Возвращает ключ ингредиента в карте по его номенклатуре: идентификатор номенклатуры."""
    return nomenclature.id


def _ingredient_key(ingredient: IngredientModel) -> uuid.UUID:
    """Возвращает ключ уникальности ингредиента в карте: идентификатор его номенклатуры."""
    return _nomenclature_key(ingredient.nomenclature)


class RecipeModel(NamedEntity):
    """Модель технологической карты (рецепта) полуфабриката или блюда (п. 2.1 ТЗ).

    Карта описывает, из чего и как получается одна номенклатурная позиция (``result``):
    состав (ингредиенты), выход, время приготовления и шаги. Карта может быть составной
    (п. 2.5 ТЗ): полуфабрикат входит в другую карту как обычный ингредиент-номенклатура,
    а его собственную карту находят по результату (``result``), см. слой Logics.

    Веса брутто и нетто — суммы по ингредиентам. Они не хранятся, а вычисляются при каждом
    обращении, поэтому добавление, удаление ингредиента или изменение его количества и потерь
    сразу отражаются в расчёте. Вес вложенного полуфабриката берётся по его количеству в строке,
    а не рекурсивно по его карте.

    Брутто, нетто и выход — три разные величины, и друг с другом они не сверяются:

    - брутто — исходный вес учтённых ингредиентов;
    - нетто — вес этих ингредиентов после потерь, то есть то, что от них осталось в продукте;
    - вес выхода — ``output_quantity * result.grams_per_base_unit``, сколько продукта получилось.

    Они расходятся по разным причинам. Вода «вне учёта» (например, 3500 мл при варке бульона) не является
    ингредиентом: на складе её нет, и списывать её нельзя. Упаковка входит в состав и в нетто, но не в вес
    блюда. Поэтому нетто нельзя проверять на равенство выходу. Расчёты на единицу продукции (масштабирование
    состава под нужное количество, стоимость, калорийность на 100 г) идут по выходу, а не по нетто.
    Нетто — справочный вес учтённых ингредиентов.

    Проектные решения:

    - ``result`` задаётся только в конструкторе и не имеет сеттера: по нему в хранилище
      определяется единственная карта позиции и находится карта полуфабриката.
    - Номенклатура ингредиента уникальна в рамках карты: ключ коллекции — её идентификатор.
      Поэтому ингредиент добавляется и удаляется по номенклатуре.
    - Защита от циклов здесь только локальная: результат не может быть ингредиентом собственной
      карты. Цикл через несколько карт (A включает B, B включает A) обнаруживается в слое Logics,
      где карты видны вместе.
    - Карта без ингредиентов допустима, её вес равен нулю: иначе карту нельзя собирать по частям.
    - Шаги и список ингредиентов возвращаются копиями, чтобы изменить карту в обход проверок было нельзя.
    """

    # Типы номенклатуры, которые могут быть результатом карты: готовятся по карте (DomainEntities.md)
    RESULT_TYPES: ClassVar[frozenset[NomenclatureType]] = frozenset(
        {NomenclatureType.SEMI_FINISHED, NomenclatureType.DISH}
    )

    # Номенклатура, получаемая по карте
    _result: NomenclatureModel
    # Выход в базовой единице результата
    _output_quantity: int | float
    # Время приготовления в минутах
    _cooking_time_minutes: int | float
    # Шаги приготовления
    _steps: list[str]
    # Ингредиенты, уникальные по номенклатуре
    _ingredients: UniqueCollection[IngredientModel]

    def __init__(
        self,
        name: str,
        result: NomenclatureModel,
        output_quantity: float,
        cooking_time_minutes: float,
        steps: list[str],
        ingredients: Iterable[IngredientModel] = (),
    ) -> None:
        """Инициализирует технологическую карту.

        :param name: Наименование карты.
        :param result: Номенклатура-результат: полуфабрикат или блюдо.
        :param output_quantity: Выход в базовой единице результата, число больше нуля.
            Вес выхода равен ``output_quantity * result.grams_per_base_unit``.
        :param cooking_time_minutes: Время приготовления в минутах, число больше нуля.
        :param steps: Шаги приготовления, непустой список непустых строк.
        :param ingredients: Начальный состав карты, по умолчанию пустой.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям,
            в составе повторяется номенклатура или встречается результат карты.
        """
        super().__init__(name)
        result = CommonValidator.validate_instance(result, NomenclatureModel, "result", "Ожидается номенклатура")
        if result.type not in self.RESULT_TYPES:
            raise ArgumentsException("result", "Результатом карты может быть только полуфабрикат или блюдо")
        self._result = result
        self.output_quantity = output_quantity
        self.cooking_time_minutes = cooking_time_minutes
        self.steps = steps
        self._ingredients = UniqueCollection(_ingredient_key)
        for ingredient in ingredients:
            self.add_ingredient(ingredient)

    @property
    def result(self) -> NomenclatureModel:
        """Возвращает номенклатуру-результат карты.

        Только для чтения: задаётся в конструкторе.
        """
        return self._result

    @property
    def output_quantity(self) -> int | float:
        """Возвращает выход в базовой единице результата."""
        return self._output_quantity

    @output_quantity.setter
    def output_quantity(self, value: float) -> None:
        """Устанавливает выход в базовой единице результата.

        :param value: Новый выход, конечное число больше нуля.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        self._output_quantity = CommonValidator.validate_positive_number(value, "output_quantity")

    @property
    def cooking_time_minutes(self) -> int | float:
        """Возвращает время приготовления в минутах."""
        return self._cooking_time_minutes

    @cooking_time_minutes.setter
    def cooking_time_minutes(self, value: float) -> None:
        """Устанавливает время приготовления в минутах.

        :param value: Новое время в минутах, конечное число больше нуля.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        self._cooking_time_minutes = CommonValidator.validate_positive_number(value, "cooking_time_minutes")

    @property
    def steps(self) -> list[str]:
        """Возвращает копию списка шагов приготовления."""
        return list(self._steps)

    @steps.setter
    def steps(self, value: list[str]) -> None:
        """Устанавливает шаги приготовления, заменяя прежние.

        Строки очищаются от пробелов по краям. Строка вместо списка не принимается:
        она итерируема и была бы разобрана на отдельные символы.

        :param value: Новые шаги, непустой список непустых строк.
        :raises ArgumentsException: Если значение не список, пустое или содержит не строку
            либо пустую строку. Прежние шаги при ошибке не меняются.
        """
        steps = cast(list[object], CommonValidator.validate_instance(value, list, "steps", "Ожидается список шагов"))
        if not steps:
            raise ArgumentsException("steps", "Список шагов не может быть пустым")

        self._steps = [CommonValidator.validate_string(step, "steps") for step in steps]

    @property
    def ingredients(self) -> list[IngredientModel]:
        """Возвращает копию списка ингредиентов в порядке добавления."""
        return list(self._ingredients)

    @property
    def gross_weight(self) -> float:
        """Возвращает вес брутто карты в граммах: сумму брутто всех ингредиентов."""
        return sum((ingredient.gross_weight for ingredient in self._ingredients), 0.0)

    @property
    def net_weight(self) -> float:
        """Возвращает вес нетто карты в граммах: сумму нетто всех ингредиентов."""
        return sum((ingredient.net_weight for ingredient in self._ingredients), 0.0)

    def add_ingredient(self, ingredient: IngredientModel) -> None:
        """Добавляет ингредиент в состав карты.

        :param ingredient: Добавляемый ингредиент.
        :raises ArgumentsException: Если значение не ингредиент, номенклатура ингредиента
            совпадает с результатом карты или уже есть в составе.
        """
        ingredient = CommonValidator.validate_instance(
            ingredient, IngredientModel, "ingredient", "Ожидается ингредиент"
        )
        if ingredient.nomenclature == self._result:
            raise ArgumentsException("ingredient", "Результат карты не может быть ингредиентом этой же карты")

        self._ingredients.add(ingredient)

    def remove_ingredient(self, nomenclature: NomenclatureModel) -> None:
        """Удаляет из состава карты ингредиент с указанной номенклатурой.

        :param nomenclature: Номенклатура удаляемого ингредиента.
        :raises ArgumentsException: Если значение не номенклатура или такой номенклатуры нет в составе.
        """
        nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        self._ingredients.remove(_nomenclature_key(nomenclature))
