import uuid
from collections.abc import Iterable
from typing import ClassVar, cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.named_entity import NamedEntity
from Src.Core.nomenclature_type import NomenclatureType
from Src.Core.unique_collection import UniqueCollection
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_catalog import NomenclatureCatalog
from Src.Models.nomenclature_model import NomenclatureModel


class RecipeModel(NamedEntity):
    """Модель технологической карты (рецепта) полуфабриката или блюда (п. 2.1 ТЗ).

    Карта описывает, из чего и как получается одна номенклатурная позиция (``result``):
    состав, выход, время приготовления и шаги. Состав — ингредиенты (``IngredientModel``): сырьё и упаковка
    с пустым основанием, а полуфабрикаты и блюда со своей картой (п. 2.5 ТЗ) — с основанием, собранным
    из их карты методом ``as_ingredient``.

    Веса брутто и нетто вычисляются динамически при каждом обращении (паттерн «Компоновщик» / Composite):
    карта суммирует веса ингредиентов, не различая сырьё и полуфабрикаты, а составной ингредиент
    сам считает вес рекурсивно по основанию.

    Брутто, нетто и выход:
    - брутто — суммарный вес исходного сырья, необходимого для приготовления (с учётом сырья во вложенных картах);
    - нетто — суммарный вес элементов после всех стадий обработки и потерь;
    - выход (output_quantity) — плановый объём или масса готового продукта по карте.
    Для масштабирования карты под произвольный выход (например, порция 200 г при базовой карте на 400 г)
    предусмотрены методы gross_weight_for и net_weight_for.

    Проектные решения:

    - ``result`` задаётся только в конструкторе и не имеет сеттера: по нему в хранилище
      определяется единственная карта позиции и находится карта полуфабриката.
    - Номенклатура элемента уникальна в рамках карты: ключ коллекции — её идентификатор.
      Поэтому элемент добавляется и удаляется по номенклатуре.
    - Карта полуфабриката входит в другую карту снимком (``as_ingredient``), а не живой ссылкой:
      основание строки — производные данные, масштабированные под её количество. Правка карты
      полуфабриката уже собранные строки не меняет; каскадную пересборку в будущем возьмёт на себя
      наблюдатель (паттерн «Наблюдатель»). Цикл импортов не возникает: карта знает ингредиент, но не наоборот.
    - Снимок неизменяем снаружи и включает только ранее созданные узлы, поэтому циклы по ссылкам
      невозможны. Карта лишь проверяет, что её результат не встречается в дереве добавляемой строки
      (``IngredientModel.contains``): иначе карта включила бы снимок самой себя.
    - Карта без элементов допустима, её вес равен нулю: иначе карту нельзя собирать по частям.
    - Шаги и список элементов возвращаются копиями, чтобы изменить карту в обход проверок было нельзя.
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
    # Элементы состава, уникальные по номенклатуре
    _items: UniqueCollection[IngredientModel]

    def __init__(
        self,
        name: str,
        result: NomenclatureModel,
        output_quantity: float,
        cooking_time_minutes: float,
        steps: list[str],
        items: Iterable[IngredientModel] = (),
    ) -> None:
        """Инициализирует технологическую карту.

        :param name: Наименование карты.
        :param result: Номенклатура-результат: полуфабрикат или блюдо.
        :param output_quantity: Выход в базовой единице результата, число больше нуля.
            Вес выхода равен ``output_quantity * result.grams_per_base_unit``.
        :param cooking_time_minutes: Время приготовления в минутах, число больше нуля.
        :param steps: Шаги приготовления, непустой список непустых строк.
        :param items: Начальный состав карты (ингредиенты), по умолчанию пустой.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям,
            в составе повторяется номенклатура или встречается результат карты (в том числе в основании).
        """
        super().__init__(name)
        result = CommonValidator.validate_instance(result, NomenclatureModel, "result", "Ожидается номенклатура")
        if result.type not in self.RESULT_TYPES:
            raise ArgumentsException("result", "Результатом карты может быть только полуфабрикат или блюдо")
        self._result = result
        self.output_quantity = output_quantity
        self.cooking_time_minutes = cooking_time_minutes
        self.steps = steps
        self._items = UniqueCollection(IngredientModel.nomenclature_key)
        for item in items:
            self.add_item(item)

    @property
    def result(self) -> NomenclatureModel:
        """Возвращает номенклатуру-результат карты.

        Только для чтения: задаётся в конструкторе.
        """
        return self._result

    def result_key(self) -> uuid.UUID:
        """Возвращает ключ уникальности карты: идентификатор номенклатуры-результата (одна карта на позицию).

        Передаётся как функция ключа в UniqueCollection: ``UniqueCollection(RecipeModel.result_key)``.
        """
        return self._result.id

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
    def items(self) -> list[IngredientModel]:
        """Возвращает копию списка ингредиентов состава в порядке добавления."""
        return list(self._items)

    @property
    def gross_weight(self) -> float:
        """Возвращает вес брутто карты в граммах: сумму брутто всех ингредиентов (с учётом оснований)."""
        return sum((item.gross_weight for item in self._items), 0.0)

    @property
    def net_weight(self) -> float:
        """Возвращает вес нетто карты в граммах: сумму нетто всех ингредиентов (с учётом оснований)."""
        return sum((item.net_weight for item in self._items), 0.0)

    def gross_weight_for(self, output_quantity: float) -> float:
        """Возвращает вес брутто карты в граммах, масштабированный под указанный выход.

        Используется для расчёта веса сырья при изменении размера порции (например,
        порция 200 г при базовой карте на 400 г).

        :param output_quantity: Желаемый выход в базовой единице результата, число больше нуля.
        :return: Масштабированный вес брутто в граммах.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        output_quantity = CommonValidator.validate_positive_number(output_quantity, "output_quantity")
        ratio = output_quantity / self._output_quantity
        return self.gross_weight * ratio

    def net_weight_for(self, output_quantity: float) -> float:
        """Возвращает вес нетто карты в граммах, масштабированный под указанный выход.

        Используется для расчёта веса нетто при изменении размера порции (например,
        порция 200 г при базовой карте на 400 г).

        :param output_quantity: Желаемый выход в базовой единице результата, число больше нуля.
        :return: Масштабированный вес нетто в граммах.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        output_quantity = CommonValidator.validate_positive_number(output_quantity, "output_quantity")
        ratio = output_quantity / self._output_quantity
        return self.net_weight * ratio

    def add_item(self, item: IngredientModel) -> None:
        """Добавляет ингредиент (сырьё или собранный полуфабрикат) в состав карты.

        :param item: Добавляемый ингредиент.
        :raises ArgumentsException: Если значение не ингредиент, его номенклатура совпадает
            с результатом карты, уже есть в составе или результат карты встречается в его основании.
        """
        item = CommonValidator.validate_instance(item, IngredientModel, "item", "Ожидается ингредиент")
        if item.nomenclature == self._result:
            raise ArgumentsException("item", "Результат карты не может входить в состав этой же карты")
        if item.contains(self._result):
            raise ArgumentsException("item", "Результат карты не может входить в основание ингредиента")

        self._items.add(item)

    def remove_item(self, nomenclature: NomenclatureModel) -> None:
        """Удаляет из состава карты элемент с указанной номенклатурой.

        :param nomenclature: Номенклатура удаляемого элемента.
        :raises ArgumentsException: Если значение не номенклатура или такой номенклатуры нет в составе.
        """
        nomenclature = CommonValidator.validate_instance(
            nomenclature, NomenclatureModel, "nomenclature", "Ожидается номенклатура"
        )
        # Ключ элемента в карте — идентификатор его номенклатуры (см. IngredientModel.nomenclature_key)
        self._items.remove(nomenclature.id)

    def as_ingredient(self, quantity: float, loss_ratio: float = 0) -> IngredientModel:
        """Собирает из карты ингредиент для состава другой карты (п. 2.5 ТЗ).

        Номенклатура ингредиента — результат карты, основание — копия состава, масштабированная
        под количество: ``quantity / output_quantity``. Снимок не следит за картой: после её правки
        строку нужно собрать заново. Из карты без состава получается ингредиент без основания,
        его вес считается как у сырья.

        :param quantity: Количество в базовой единице результата карты, число больше нуля.
        :param loss_ratio: Доля потерь при приготовлении в составе другой карты,
            от 0 включительно до 1 не включая. По умолчанию 0: потерь нет.
        :return: Новый ингредиент.
        :raises ArgumentsException: Если количество или доля потерь не соответствуют требованиям.
        """
        quantity = CommonValidator.validate_positive_number(quantity, "quantity")
        factor = quantity / self._output_quantity
        return IngredientModel(self._result, quantity, loss_ratio, [item.scaled(factor) for item in self._items])

    @staticmethod
    def create_beef_bouillon(catalog: NomenclatureCatalog) -> "RecipeModel":
        """Фабричный метод: создаёт карту «Бульон костный говяжий» (Recipes.md, карта 1).

        Кости, овощи, лавровый лист и перец удаляются после варки, поэтому их потери равны 0,9.

        :param catalog: Справочник номенклатуры. Нужны результат карты и все её ингредиенты.
        :return: Карта полуфабриката.
        :raises ArgumentsException: Если в справочнике нет нужной номенклатуры.
        """
        name = "Бульон костный говяжий"
        return RecipeModel(
            name,
            catalog.get(name),
            2000,
            240,
            [
                "Кости промыть и выдержать в холодной воде 1 час, воду слить.",
                "Кости залить 3500 мл холодной воды (вне учёта), довести до кипения и снять пену.",
                "Варить на слабом огне 3 часа, не допуская бурного кипения.",
                "Лук и морковь очистить, лук разрезать пополам и подпечь на сухой сковороде до тёмных краёв.",
                "За 40 минут до конца добавить овощи, лавровый лист, перец и соль.",
                "Бульон процедить, довести до 2000 мл, при необходимости упарить. Кости и овощи не используются.",
            ],
            [
                IngredientModel(catalog.get("Кости говяжьи мозговые"), 1500, 0.9),
                IngredientModel(catalog.get("Лук репчатый"), 100, 0.9),
                IngredientModel(catalog.get("Морковь"), 80, 0.9),
                IngredientModel(catalog.get("Лавровый лист"), 1, 0.9),
                IngredientModel(catalog.get("Перец чёрный горошком"), 3, 0.9),
                IngredientModel(catalog.get("Соль"), 12),
            ],
        )

    @staticmethod
    def create_boiled_beef(catalog: NomenclatureCatalog) -> "RecipeModel":
        """Фабричный метод: создаёт карту «Говядина отварная» (Recipes.md, карта 2).

        Потери: говядина теряет 38% при варке, лавровый лист удаляется (0,9), половина соли остаётся в отваре.

        :param catalog: Справочник номенклатуры. Нужны результат карты и все её ингредиенты.
        :return: Карта полуфабриката.
        :raises ArgumentsException: Если в справочнике нет нужной номенклатуры.
        """
        name = "Говядина отварная"
        return RecipeModel(
            name,
            catalog.get(name),
            500,
            120,
            [
                "Мякоть зачистить от плёнок и сухожилий, нарезать кусками по 200–250 г.",
                "Залить 2000 мл кипящей воды (вне учёта), добавить соль и лавровый лист.",
                "Варить на слабом огне 1,5 часа до мягкости, готовое мясо остудить в отваре.",
                "Отвар не используется. Мясо нарезать полосками, дать выход 500 г.",
            ],
            [
                IngredientModel(catalog.get("Говядина (мякоть)"), 800, 0.38),
                IngredientModel(catalog.get("Лавровый лист"), 1, 0.9),
                IngredientModel(catalog.get("Соль"), 8, 0.5),
            ],
        )

    @staticmethod
    def create_beet_fry(catalog: NomenclatureCatalog) -> "RecipeModel":
        """Фабричный метод: создаёт карту «Зажарка свекольная» (Recipes.md, карта 3).

        :param catalog: Справочник номенклатуры. Нужны результат карты и все её ингредиенты.
        :return: Карта полуфабриката.
        :raises ArgumentsException: Если в справочнике нет нужной номенклатуры.
        """
        name = "Зажарка свекольная"
        return RecipeModel(
            name,
            catalog.get(name),
            700,
            30,
            [
                "Свёклу и морковь очистить и натереть на крупной тёрке, лук нарезать кубиком.",
                "На сковороде разогреть масло, обжарить лук 3 минуты до прозрачности.",
                "Добавить морковь, жарить ещё 4 минуты, затем свёклу.",
                "Влить уксус (сохраняет цвет свёклы), всыпать сахар и соль, тушить 5 минут.",
                "Добавить томатную пасту, перемешать, тушить 10 минут до мягкости свёклы.",
            ],
            [
                IngredientModel(catalog.get("Свёкла"), 400, 0.05),
                IngredientModel(catalog.get("Морковь"), 120, 0.05),
                IngredientModel(catalog.get("Лук репчатый"), 120, 0.1),
                IngredientModel(catalog.get("Томатная паста"), 50, 0.1),
                IngredientModel(catalog.get("Масло подсолнечное"), 40, 0.1),
                IngredientModel(catalog.get("Уксус 9%"), 10, 0.5),
                IngredientModel(catalog.get("Сахар"), 10),
                IngredientModel(catalog.get("Соль"), 5),
            ],
        )

    @staticmethod
    def create_borscht(
        catalog: NomenclatureCatalog,
        bouillon: "RecipeModel | None" = None,
        boiled_beef: "RecipeModel | None" = None,
        beet_fry: "RecipeModel | None" = None,
    ) -> "RecipeModel":
        """Фабричный метод: создаёт карту «Борщ с говядиной» (Recipes.md, карта 4).

        Состав включает три полуфабриката (бульон, отварная говядина, зажарка) и упаковку.
        Каждый полуфабрикат входит в состав снимком своей карты (``as_ingredient``, паттерн «Компоновщик»),
        поэтому брутто и нетто считаются рекурсивно. Карту, которую не передали, фабрика создаёт
        из справочника; если это не получается, ошибка не скрывается. Чтобы борщ был собран из карт,
        лежащих в хранилище, передавайте их явно.

        :param catalog: Справочник номенклатуры. Нужны результат карты, все её ингредиенты
            и всё, что нужно для создания не переданных карт полуфабрикатов.
        :param bouillon: Карта бульона. Если None, создаётся из справочника.
        :param boiled_beef: Карта отварной говядины. Если None, создаётся из справочника.
        :param beet_fry: Карта зажарки. Если None, создаётся из справочника.
        :return: Карта блюда.
        :raises ArgumentsException: Если в справочнике нет нужной номенклатуры.
        """
        name = "Борщ с говядиной"
        if bouillon is None:
            bouillon = RecipeModel.create_beef_bouillon(catalog)
        if boiled_beef is None:
            boiled_beef = RecipeModel.create_boiled_beef(catalog)
        if beet_fry is None:
            beet_fry = RecipeModel.create_beet_fry(catalog)

        return RecipeModel(
            name,
            catalog.get(name),
            1,
            15,
            [
                "Бульон довести до кипения, добавить картофель, нарезанный брусочками, варить 8 минут.",
                "Добавить нашинкованную капусту, варить ещё 4 минуты.",
                "Добавить зажарку и отварную говядину, прогреть 2 минуты, не допуская бурного кипения.",
                "Подавать со сметаной и рубленым укропом. Для доставки разлить в контейнер, "
                + "сметану и укроп положить сверху.",
            ],
            [
                bouillon.as_ingredient(250, 0.1),
                boiled_beef.as_ingredient(60, 0.05),
                beet_fry.as_ingredient(70, 0.05),
                IngredientModel(catalog.get("Картофель"), 80, 0.15),
                IngredientModel(catalog.get("Капуста белокочанная"), 70, 0.15),
                IngredientModel(catalog.get("Сметана 20%"), 20),
                IngredientModel(catalog.get("Укроп"), 3),
                IngredientModel(catalog.get("Контейнер для супа 500 мл"), 1),
            ],
        )
