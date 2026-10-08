import uuid
from typing import ClassVar, Self, cast, override

from Src.Core.abstract_manager import AbstractManager
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
from Src.Core.unique_collection import UniqueCollection
from Src.Logics.settings_manager import SettingsManager
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.warehouse_model import WarehouseModel


def _name_key(entity: NamedEntity) -> str:
    """Возвращает ключ уникальности по наименованию без учёта регистра."""
    return entity.name.casefold()


def _result_key(recipe: RecipeModel) -> uuid.UUID:
    """Возвращает ключ уникальности карты: идентификатор номенклатуры-результата (одна карта на позицию)."""
    return recipe.result.id


class StorageManager(AbstractManager):
    """Хранилище коллекций доменных моделей (Singleton).

    Коллекции единиц, групп, номенклатуры и складов не содержат дубликатов по наименованию
    (без учёта регистра). Коллекция технологических карт содержит не более одной карты
    на номенклатуру-результат; карту полуфабриката находит ``find_recipe()``.
    При первом запуске (флаг ``is_first_start`` в настройках) ``load()`` наполняет
    коллекции начальными данными. Иначе коллекции остаются пустыми: загружать
    данные пока неоткуда, чтение из БД появится вместе с SQLite.

    Хранилище зависит от менеджера настроек: ``load()`` принимает его параметром,
    по умолчанию берёт единственный экземпляр SettingsManager. Настройки должны быть
    загружены заранее, сам ``load()`` их не загружает.

    Начальные данные формируются здесь же, в приватных методах, через фабричные методы моделей:
    единицы, группы, склады, номенклатура и четыре карты из Recipes.md. Когда их станет много
    (рестораны, сотрудники), их стоит вынести в отдельный класс.
    """

    # Единственный экземпляр этого класса
    _instance: ClassVar["StorageManager | None"] = None

    # Единицы измерения
    _ranges: UniqueCollection[RangeModel]
    # Группы номенклатуры
    _nomenclature_groups: UniqueCollection[NomenclatureGroupModel]
    # Номенклатура
    _nomenclatures: UniqueCollection[NomenclatureModel]
    # Склады
    _warehouses: UniqueCollection[WarehouseModel]
    # Технологические карты, по одной на номенклатуру-результат
    _recipes: UniqueCollection[RecipeModel]

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса, при первом обращении создаёт его.

        Состояние готовится здесь, а не в __init__: Python вызывает __init__
        при каждом обращении к классу. Экземпляр ищется в cls.__dict__, а не через
        getattr, чтобы наследник не получил экземпляр родителя.
        """
        instance = cast(Self | None, cls.__dict__.get("_instance"))
        if instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            # Сохранение после хука: если он упадёт, полусозданного экземпляра не останется
            cls._instance = instance
        return instance

    @override
    def _initialize(self) -> None:
        """Готовит флаг загрузки и создаёт пустые коллекции."""
        super()._initialize()
        self._reset_collections()

    def _reset_collections(self) -> None:
        """Создаёт пустые коллекции сущностей.

        Вызывается при создании экземпляра и в load() для сброса состояния.
        """
        self._ranges = UniqueCollection(_name_key)
        self._nomenclature_groups = UniqueCollection(_name_key)
        self._nomenclatures = UniqueCollection(_name_key)
        self._warehouses = UniqueCollection(_name_key)
        self._recipes = UniqueCollection(_result_key)

    @override
    def load(self, settings_manager: SettingsManager | None = None) -> None:
        """Пересоздаёт коллекции и при первом запуске наполняет их начальными данными.

        Флаг is_loaded выставляется только после успеха.

        :param settings_manager: Менеджер настроек, от которого зависит хранилище,
            None — единственный экземпляр SettingsManager. Настройки в нём должны быть загружены.
        :raises OperationException: Если настройки не загружены или начальные данные
            содержат дубликаты.
        """
        self._is_loaded = False
        # Зависимость разрешается здесь, а не в _initialize: хук не должен зависеть от других менеджеров
        if settings_manager is None:
            settings_manager = SettingsManager()
        is_first_start = settings_manager.settings.is_first_start

        self._reset_collections()
        if is_first_start:
            try:
                self._fill_first_start_data()
            except ArgumentsException as ex:
                self._reset_collections()
                raise OperationException(f"Не удалось сформировать начальные данные: {ex}") from ex
        self._is_loaded = True

    def _fill_first_start_data(self) -> None:
        """Наполняет коллекции начальными данными.

        Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях, а карты —
        на те же объекты номенклатуры: каждый объект создаётся один раз и добавляется в коллекцию.
        Карты регистрируются от полуфабрикатов к блюду: так проверка циклов видит вложенные карты.

        :raises ArgumentsException: Если начальные данные содержат дубликаты или цикл между картами.
        """
        kilogram = RangeModel.create_kilogram()
        liter = RangeModel.create_liter()
        for unit in (kilogram.base, kilogram, liter.base, liter, RangeModel.create_piece()):
            self._ranges.add(unit)

        for group in (
            NomenclatureGroupModel.create_meat(),
            NomenclatureGroupModel.create_dairy(),
            NomenclatureGroupModel.create_vegetables(),
            NomenclatureGroupModel.create_grocery(),
            NomenclatureGroupModel.create_semi_finished(),
            NomenclatureGroupModel.create_dishes(),
            NomenclatureGroupModel.create_packaging(),
        ):
            self._nomenclature_groups.add(group)

        for nomenclature in self._create_nomenclatures():
            self._nomenclatures.add(nomenclature)

        for warehouse in (
            WarehouseModel.create_restaurant_warehouse(),
            WarehouseModel.create_workshop_warehouse(),
        ):
            self._warehouses.add(warehouse)

        nomenclatures = {item.name: item for item in self._nomenclatures}
        for recipe in (
            RecipeModel.create_beef_bouillon(nomenclatures),
            RecipeModel.create_boiled_beef(nomenclatures),
            RecipeModel.create_beet_fry(nomenclatures),
            RecipeModel.create_borscht(nomenclatures),
        ):
            self._add_recipe(recipe)

    def _create_nomenclatures(self) -> list[NomenclatureModel]:
        """Создаёт начальную номенклатуру на основе уже заполненных единиц и групп.

        Три старые позиции (Говядина, Молоко, Стакан) остаются, остальные нужны картам из Recipes.md.
        Вес базовой единицы: для граммов и миллилитров воды — 1, для масла — плотность, для штучных — вес штуки.

        :return: Список номенклатуры в порядке добавления.
        """
        ranges = {item.name: item for item in self._ranges}
        groups = {item.name: item for item in self._nomenclature_groups}
        kilogram, liter, piece = ranges["килограмм"], ranges["литр"], ranges["штука"]
        meat, dairy = groups["Мясные продукты"], groups["Молочные продукты"]
        vegetables, grocery = groups["Овощи"], groups["Бакалея"]
        semi_finished, dishes, packaging = groups["Полуфабрикаты"], groups["Блюда"], groups["Упаковка"]
        raw = NomenclatureModel.create_raw_material
        semi = NomenclatureModel.create_semi_finished

        return [
            raw("Говядина", "Говядина охлаждённая", meat, kilogram, 1),
            # Плотность молока принята за 1 г/мл
            raw("Молоко", "Молоко пастеризованное 3,2%", dairy, liter, 1),
            NomenclatureModel.create_packaging("Стакан", "Стакан бумажный 300 мл", packaging, piece, 10),
            raw("Кости говяжьи мозговые", "Кости говяжьи мозговые охлаждённые", meat, kilogram, 1),
            raw("Говядина (мякоть)", "Говядина (мякоть) охлаждённая", meat, kilogram, 1),
            raw("Лук репчатый", "Лук репчатый свежий", vegetables, kilogram, 1),
            raw("Морковь", "Морковь столовая свежая", vegetables, kilogram, 1),
            raw("Свёкла", "Свёкла столовая свежая", vegetables, kilogram, 1),
            raw("Картофель", "Картофель свежий", vegetables, kilogram, 1),
            raw("Капуста белокочанная", "Капуста белокочанная свежая", vegetables, kilogram, 1),
            raw("Укроп", "Укроп свежий", vegetables, kilogram, 1),
            # Один лавровый лист весит около 0,5 г
            raw("Лавровый лист", "Лавровый лист сушёный", grocery, piece, 0.5),
            raw("Перец чёрный горошком", "Перец чёрный горошком", grocery, kilogram, 1),
            raw("Соль", "Соль пищевая поваренная", grocery, kilogram, 1),
            raw("Томатная паста", "Томатная паста", grocery, kilogram, 1),
            # Плотность подсолнечного масла около 0,92 г/мл
            raw("Масло подсолнечное", "Масло подсолнечное рафинированное", grocery, liter, 0.92),
            raw("Уксус 9%", "Уксус столовый 9%", grocery, liter, 1),
            raw("Сахар", "Сахар-песок", grocery, kilogram, 1),
            raw("Сметана 20%", "Сметана 20% жирности", dairy, kilogram, 1),
            NomenclatureModel.create_packaging(
                "Контейнер для супа 500 мл",
                "Контейнер для супа 500 мл (только для доставки, п. 3.3 ТЗ)",
                packaging,
                piece,
                20,
            ),
            # Плотность бульона принята за 1 г/мл
            semi("Бульон костный говяжий", "Бульон костный говяжий (полуфабрикат)", semi_finished, liter, 1),
            semi("Говядина отварная", "Говядина отварная нарезанная (полуфабрикат)", semi_finished, kilogram, 1),
            semi("Зажарка свекольная", "Зажарка свекольная (полуфабрикат)", semi_finished, kilogram, 1),
            # Порция борща — 500 г
            NomenclatureModel.create_dish("Борщ с говядиной", "Борщ с говядиной, порция 500 г", dishes, piece, 500),
        ]

    def _add_recipe(self, recipe: RecipeModel) -> None:
        """Регистрирует технологическую карту в хранилище.

        Проверка циклов глубокая: локально её делает сама карта (результат не входит в свой состав),
        здесь обходятся карты вложенных полуфабрикатов. Карты вложенных полуфабрикатов
        должны быть зарегистрированы заранее, иначе их состав не виден.

        :param recipe: Регистрируемая карта.
        :raises ArgumentsException: Если на результат уже есть карта или карта замыкает цикл включений.
        """
        if self._creates_cycle(recipe):
            raise ArgumentsException("recipe", f"Карта «{recipe.name}» образует цикл включений")
        self._recipes.add(recipe)

    def _creates_cycle(self, recipe: RecipeModel) -> bool:
        """Проверяет, входит ли результат карты в состав её вложенных карт (прямо или через цепочку).

        :param recipe: Проверяемая карта, ещё не добавленная в хранилище.
        :return: True, если результат карты достижим из её ингредиентов через карты полуфабрикатов.
        """
        visited: set[uuid.UUID] = set()
        pending = [ingredient.nomenclature for ingredient in recipe.ingredients]
        while pending:
            nomenclature = pending.pop()
            if nomenclature is recipe.result:
                return True
            if nomenclature.id in visited:
                continue

            visited.add(nomenclature.id)
            nested = self.find_recipe(nomenclature)
            if nested is not None:
                pending.extend(ingredient.nomenclature for ingredient in nested.ingredients)
        return False

    def find_recipe(self, nomenclature: NomenclatureModel) -> RecipeModel | None:
        """Возвращает технологическую карту, результатом которой является номенклатура.

        :param nomenclature: Искомая номенклатура-результат.
        :return: Карта или None, если карты нет (например, у сырья).
        """
        return next((recipe for recipe in self._recipes if recipe.result is nomenclature), None)

    @property
    def ranges(self) -> list[RangeModel]:
        """Возвращает копию списка единиц измерения."""
        return list(self._ranges)

    @property
    def nomenclature_groups(self) -> list[NomenclatureGroupModel]:
        """Возвращает копию списка групп номенклатуры."""
        return list(self._nomenclature_groups)

    @property
    def nomenclatures(self) -> list[NomenclatureModel]:
        """Возвращает копию списка номенклатуры."""
        return list(self._nomenclatures)

    @property
    def warehouses(self) -> list[WarehouseModel]:
        """Возвращает копию списка складов."""
        return list(self._warehouses)

    @property
    def recipes(self) -> list[RecipeModel]:
        """Возвращает копию списка технологических карт."""
        return list(self._recipes)
