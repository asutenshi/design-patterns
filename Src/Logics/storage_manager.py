import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Self, cast, override

from Src.Core.abstract_manager import AbstractManager
from Src.Core.abstract_model import AbstractModel
from Src.Core.common_validator import CommonValidator
from Src.Core.entity_type import EntityType
from Src.Core.exception import (
    ArgumentsException,
    OperationException,
    ReferencedEntityException,
)
from Src.Core.named_entity import NamedEntity
from Src.Core.unique_collection import UniqueCollection
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Logics.settings_manager import SettingsManager
from Src.Models.nomenclature_catalog import NomenclatureCatalog
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.warehouse_model import WarehouseModel


class StorageManager(AbstractManager):
    """Хранилище коллекций доменных моделей (Singleton).

    Коллекции единиц, групп, номенклатуры и складов не содержат дубликатов по наименованию
    (без учёта регистра). Коллекция технологических карт содержит не более одной карты
    на номенклатуру-результат; карту полуфабриката находит ``find_recipe()``.
    Сущность по типу и коду находит ``find()``, сущности, ссылающиеся на сущность с заданным кодом, —
    ``find_referrers()``.

    Изменяют хранилище ``create``, ``put``, ``patch`` и ``delete``: их будет вызывать API. Данные приходят
    словарём в формате выгрузки (``ConverterFactory``): поля модели, вложенные сущности хранилища задаются
    ссылкой ``{"id": ...}``, а ``model_type`` можно не указывать, его задаёт тип сущности. Правила:

    - Все ссылки новой сущности должны вести на сущности хранилища (те же объекты), иначе ошибка аргумента.
    - Удалить сущность или сменить ей код (``id``) нельзя, пока на неё ссылаются другие сущности
      (``ReferencedEntityException``). Менять остальные поля можно: ссылающиеся сущности видят изменения,
      потому что сущность меняется на месте (``BaseEntity.replace_state``), а не заменяется.
    - Операция атомарна: все проверки идут до первого изменения коллекций, при ошибке хранилище не меняется.
    - Каскадной пересборки снимков карт полуфабрикатов при правке сущностей пока нет.
    Источник данных ``load()`` выбирает так:

    - указан файл (``file_name``) — коллекции читаются из JSON-файла в формате выгрузки через
      ``ConverterFactory``; настройки при этом не нужны и не читаются. Какие коллекции есть в хранилище,
      описано один раз, в ``_collections()``, а порядок их загрузки задаёт файл: модели в нём записаны
      целиком, поэтому порядок на результат не влияет;
    - файла нет, и в настройках стоит флаг ``is_first_start`` — коллекции наполняются начальными данными;
    - иначе коллекции остаются пустыми: чтение из БД появится вместе с SQLite.

    Хранилище зависит от менеджера настроек: ``load()`` принимает его параметром,
    по умолчанию берёт единственный экземпляр SettingsManager. Настройки должны быть
    загружены заранее, сам ``load()`` их не загружает.

    Начальные данные формируются здесь же, в приватных методах, через фабричные методы моделей:
    единицы, группы, склады, номенклатура и четыре карты из Recipes.md. Когда их станет много
    (рестораны, сотрудники), их стоит вынести в отдельный класс.
    """

    # Единственный экземпляр этого класса
    _instance: ClassVar["StorageManager | None"] = None

    # Класс модели для каждого типа сущности: по нему create/put/patch собирают сущность из данных
    _ENTITY_CLASSES: ClassVar[dict[EntityType, type[NamedEntity]]] = {
        EntityType.NOMENCLATURE: NomenclatureModel,
        EntityType.NOMENCLATURE_GROUP: NomenclatureGroupModel,
        EntityType.RANGE: RangeModel,
        EntityType.WAREHOUSE: WarehouseModel,
        EntityType.RECIPE: RecipeModel,
    }

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
        self._ranges = UniqueCollection(NamedEntity.name_key)
        self._nomenclature_groups = UniqueCollection(NamedEntity.name_key)
        self._nomenclatures = UniqueCollection(NamedEntity.name_key)
        self._warehouses = UniqueCollection(NamedEntity.name_key)
        self._recipes = UniqueCollection(RecipeModel.result_key)

    @override
    def load(self, settings_manager: SettingsManager | None = None, file_name: str | None = None) -> None:
        """Пересоздаёт коллекции и наполняет их из файла или начальными данными.

        Флаг is_loaded выставляется только после успеха. При ошибке коллекции пусты.

        :param settings_manager: Менеджер настроек, от которого зависит хранилище,
            None — единственный экземпляр SettingsManager. Настройки в нём должны быть загружены.
            Не используется, если указан ``file_name``.
        :param file_name: Путь к JSON-файлу с выгрузкой хранилища. Если указан, данные читаются из него,
            а флаг первого запуска не учитывается. None — файл не читается.
        :raises OperationException: Если настройки не загружены, начальные данные содержат дубликаты
            либо файл недоступен, не является выгрузкой хранилища или содержит некорректные данные.
        """
        self._is_loaded = False
        if file_name is not None:
            self._reset_collections()
            self._load_from_file(file_name)
            self._is_loaded = True
            return

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

    def _collections(self) -> dict[str, Callable[[object], None]]:
        """Возвращает состав хранилища: ключ коллекции в файле и функцию, которая добавляет в неё модель.

        Ключи совпадают с именами свойств, под которыми ``ConverterFactory`` выгружает коллекции.
        Функция проверяет тип модели: тип выбирает файл (``model_type``), и в коллекцию единиц
        не должна попасть, например, группа. Новая коллекция подключается строкой здесь.

        :return: Функции добавления по ключам коллекций.
        """
        return {
            "ranges": self._adder(RangeModel, self._ranges),
            "nomenclature_groups": self._adder(NomenclatureGroupModel, self._nomenclature_groups),
            "nomenclatures": self._adder(NomenclatureModel, self._nomenclatures),
            "warehouses": self._adder(WarehouseModel, self._warehouses),
            "recipes": self._adder(RecipeModel, self._recipes),
        }

    @staticmethod
    def _adder[T](model_type: type[T], collection: UniqueCollection[T]) -> Callable[[object], None]:
        """Возвращает функцию, которая проверяет тип модели и добавляет её в коллекцию.

        :param model_type: Тип моделей коллекции.
        :param collection: Коллекция хранилища.
        :return: Функция добавления. Она бросает ArgumentsException, если модель другого типа
            или повторяется в коллекции.
        """

        def add(model: object) -> None:
            collection.add(
                CommonValidator.validate_instance(model, model_type, "model", f"Ожидается {model_type.__name__}")
            )

        return add

    def _load_from_file(self, file_name: str) -> None:
        """Наполняет коллекции из JSON-файла с выгрузкой хранилища.

        Коллекции загружаются в том порядке, в каком они записаны в файле, и в одной сессии десериализации.
        Модель, которая встречается в файле много раз (в своей коллекции и внутри других моделей), собирается
        при первой встрече и дальше берётся из кэша. Поэтому порядок коллекций не важен, а единица измерения,
        группа и номенклатура становятся одним объектом. Это важно для ``find_recipe``, который сравнивает
        номенклатуры по тождеству. Лишние ключи файла (``is_loaded``) игнорируются.

        :param file_name: Путь к файлу.
        :raises OperationException: Если файл недоступен, не является выгрузкой хранилища, в нём нет
            коллекции, данные некорректны или содержат дубликаты. Коллекции при этом очищаются.
        """
        path = Path(file_name)
        try:
            data = self._read_file(path)
            collections = self._collections()
            missing = [key for key in collections if key not in data]
            if missing:
                raise OperationException(f"В файле хранилища нет коллекций: {', '.join(missing)}")

            factory = DeserializerFactory()
            with factory.session():
                for key, items in data.items():
                    add = collections.get(key)
                    if add is not None:
                        self._load_collection(factory, key, items, add)
        except ArgumentsException as ex:
            self._reset_collections()
            raise OperationException(f"Не удалось загрузить хранилище из файла {path}: {ex}") from ex
        except OperationException:
            self._reset_collections()
            raise

    @staticmethod
    def _read_file(path: Path) -> dict[str, object]:
        """Читает JSON-файл с выгрузкой хранилища.

        :param path: Путь к файлу.
        :return: Корневой JSON-объект.
        :raises OperationException: Если файл недоступен, не читается как UTF-8 JSON
            или его корень не объект.
        """
        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)  # pyright: ignore[reportAny]
        except (OSError, ValueError) as ex:
            raise OperationException(f"Не удалось прочитать файл хранилища {path}: {ex}") from ex

        if not isinstance(data, dict):
            raise OperationException(f"Файл хранилища {path} должен содержать JSON-объект")
        return cast(dict[str, object], data)

    @staticmethod
    def _load_collection(
        factory: DeserializerFactory, key: str, items: object, add: Callable[[object], None]
    ) -> None:
        """Десериализует одну коллекцию из данных файла и добавляет модели в коллекцию хранилища.

        :param factory: Фабрика десериализаторов с открытой сессией.
        :param key: Ключ коллекции в файле, для текста ошибки.
        :param items: Данные коллекции из файла.
        :param add: Функция, добавляющая модель в коллекцию хранилища (см. ``_collections``).
        :raises OperationException: Если в данных ссылка на неизвестную модель.
        :raises ArgumentsException: Если коллекция не список, модель некорректна, другого типа или повторяется.
        """
        models = cast(list[object], CommonValidator.validate_instance(items, list, key, "Ожидается список"))
        for item in models:
            add(factory.deserialize(item))

    def _fill_first_start_data(self) -> None:
        """Наполняет коллекции начальными данными.

        Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях, а карты —
        на те же объекты номенклатуры: каждый объект создаётся один раз и добавляется в коллекцию.
        Карты создаются от полуфабрикатов к блюду: борщ собирает полуфабрикаты снимками их карт.

        :raises ArgumentsException: Если начальные данные содержат дубликаты.
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

        catalog = NomenclatureCatalog(self._nomenclatures)
        bouillon = RecipeModel.create_beef_bouillon(catalog)
        boiled_beef = RecipeModel.create_boiled_beef(catalog)
        beet_fry = RecipeModel.create_beet_fry(catalog)
        borscht = RecipeModel.create_borscht(catalog, bouillon, boiled_beef, beet_fry)
        for recipe in (bouillon, boiled_beef, beet_fry, borscht):
            self._recipes.add(recipe)

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

    def find_recipe(self, nomenclature: NomenclatureModel) -> RecipeModel | None:
        """Возвращает технологическую карту, результатом которой является номенклатура.

        :param nomenclature: Искомая номенклатура-результат.
        :return: Карта или None, если карты нет (например, у сырья).
        """
        return next((recipe for recipe in self._recipes if recipe.result is nomenclature), None)

    def find_recipe_by_name(self, name: str) -> RecipeModel | None:
        """Возвращает технологическую карту по наименованию без учёта регистра и пробелов по краям.

        Уникальность наименований карт хранилище не гарантирует (уникален только результат),
        поэтому при совпадении нескольких возвращается первая добавленная.

        :param name: Наименование карты.
        :return: Карта или None, если карты с таким наименованием нет.
        :raises ArgumentsException: Если наименование не строка.
        """
        name = CommonValidator.validate_instance(name, str, "name", "Ожидается строка")
        key = name.strip().casefold()
        return next((recipe for recipe in self._recipes if recipe.name_key() == key), None)

    def _entity_collections(self) -> dict[EntityType, UniqueCollection[NamedEntity]]:
        """Возвращает все коллекции хранилища по типам сущностей.

        Состав коллекций для поиска и изменения задаётся здесь один раз: им пользуются ``find()``,
        ``find_referrers()``, ``create()``, ``put()``, ``patch()`` и ``delete()``. Новая коллекция подключается
        строкой здесь, значением в ``EntityType`` и классом в ``_ENTITY_CLASSES``.
        Не путать с ``_collections()``: тот описывает загрузку из файла (ключи файла и функции добавления).

        Коллекции приводятся к ``UniqueCollection[NamedEntity]``: общий код работает с ними через базовый класс,
        а тип добавляемой сущности гарантирует ``_build_entity()`` (класс берётся из ``_ENTITY_CLASSES``).

        :return: Коллекции хранилища по типам сущностей.
        """
        return {
            EntityType.NOMENCLATURE: cast(UniqueCollection[NamedEntity], self._nomenclatures),
            EntityType.NOMENCLATURE_GROUP: cast(UniqueCollection[NamedEntity], self._nomenclature_groups),
            EntityType.RANGE: cast(UniqueCollection[NamedEntity], self._ranges),
            EntityType.WAREHOUSE: cast(UniqueCollection[NamedEntity], self._warehouses),
            EntityType.RECIPE: cast(UniqueCollection[NamedEntity], self._recipes),
        }

    def find_referrers(self, target_id: uuid.UUID) -> list[NamedEntity]:
        """Возвращает сущности хранилища, которые ссылаются на сущность с указанным кодом.

        Обходит все коллекции и проверяет ``references()`` каждой сущности. Результат нужен, чтобы запретить
        удалять сущность или менять ей код, пока на неё кто-то ссылается (Docs/.homework.md, п. 3).
        Сама сущность в результат не попадает, даже если ссылается на себя (базовая единица), и сущность
        с несколькими ссылками на цель возвращается один раз. Ссылки внутри состава карты учитываются:
        сырьё, которое входит только в основание строки, тоже считается связанным с картой.

        :param target_id: Код сущности, на которую ищутся ссылки. Существование сущности не проверяется:
            для неизвестного кода результат пуст.
        :return: Сущности, ссылающиеся на цель, в порядке обхода коллекций.
        :raises ArgumentsException: Если код не UUID.
        """
        target_id = CommonValidator.validate_instance(target_id, uuid.UUID, "target_id", "Ожидается UUID")
        return [
            entity
            for collection in self._entity_collections().values()
            for entity in collection
            if entity.id != target_id and any(ref.id == target_id for ref in entity.references())
        ]

    def find(self, entity_type: EntityType, entity_id: uuid.UUID) -> NamedEntity | None:
        """Возвращает сущность указанного типа по коду.

        Ищет перебором: ключи коллекций — наименования или результат карты, а не код.

        :param entity_type: Тип сущности, определяет коллекцию поиска.
        :param entity_id: Код (идентификатор) сущности.
        :return: Сущность или None, если сущности с таким кодом нет.
        :raises ArgumentsException: Если тип не EntityType, код не UUID
            или для типа нет коллекции.
        """
        entity_type = CommonValidator.validate_instance(entity_type, EntityType, "entity_type", "Ожидается тип сущности")
        entity_id = CommonValidator.validate_instance(entity_id, uuid.UUID, "entity_id", "Ожидается UUID")
        collection = self._entity_collections().get(entity_type)
        if collection is None:
            raise ArgumentsException("entity_type", f"Поиск сущностей типа {entity_type.value} не поддерживается")

        return next((entity for entity in collection if entity.id == entity_id), None)

    def entities(self, entity_type: EntityType) -> list[NamedEntity]:
        """Возвращает копию списка сущностей указанного типа в порядке добавления.

        Общий доступ к коллекции по типу для API: свойства ``ranges``, ``nomenclatures`` и другие
        дают то же самое, но каждое для своего типа.

        :param entity_type: Тип сущности, определяет коллекцию.
        :return: Сущности этого типа; изменение списка не меняет хранилище.
        :raises ArgumentsException: Если тип не EntityType.
        """
        entity_type = CommonValidator.validate_instance(entity_type, EntityType, "entity_type", "Ожидается тип сущности")
        return list(self._entity_collections()[entity_type])

    def create(self, entity_type: EntityType, data: dict[str, object]) -> NamedEntity:
        """Создаёт сущность указанного типа из данных и добавляет её в хранилище.

        :param entity_type: Тип создаваемой сущности.
        :param data: Поля сущности в формате выгрузки. Вложенные сущности хранилища — ссылки ``{"id": ...}``.
            Если указан ``id``, он становится кодом сущности, иначе код создаётся автоматически.
        :return: Созданная сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если тип не EntityType, данные некорректны, ссылка ведёт на неизвестную
            сущность, код уже занят или такое наименование (ключ) уже есть в коллекции.
        """
        entity_type = CommonValidator.validate_instance(entity_type, EntityType, "entity_type", "Ожидается тип сущности")
        entity = self._build_entity(entity_type, data, None)
        self._ensure_id_is_free(entity)
        self._entity_collections()[entity_type].add(entity)
        return entity

    def put(self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object]) -> NamedEntity:
        """Полностью заменяет поля сущности значениями из данных, сама сущность остаётся тем же объектом.

        Поля, которых нет в данных, не сохраняются (обязательные приводят к ошибке). Если ``id`` в данных нет,
        код сущности не меняется, если он другой — сущность получает новый код, но только когда на неё
        никто не ссылается.

        :param entity_type: Тип сущности.
        :param entity_id: Текущий код сущности.
        :param data: Все поля сущности в формате выгрузки.
        :return: Изменённая сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если аргументы некорректны, сущности нет, данные некорректны, ссылка ведёт
            на неизвестную сущность, новый код или наименование (ключ) уже заняты.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        return self._update(entity_type, entity_id, data, merge=False)

    def patch(self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object]) -> NamedEntity:
        """Изменяет только указанные в данных поля сущности, остальные сохраняются.

        Слияние поверхностное: значение поля заменяется целиком, в том числе вложенный словарь.
        Остальное, как у ``put()``.

        :param entity_type: Тип сущности.
        :param entity_id: Текущий код сущности.
        :param data: Изменяемые поля сущности в формате выгрузки.
        :return: Изменённая сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если аргументы некорректны, сущности нет, данные некорректны, ссылка ведёт
            на неизвестную сущность, новый код или наименование (ключ) уже заняты.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        return self._update(entity_type, entity_id, data, merge=True)

    def delete(self, entity_type: EntityType, entity_id: uuid.UUID) -> None:
        """Удаляет сущность из хранилища, если на неё никто не ссылается.

        :param entity_type: Тип сущности.
        :param entity_id: Код сущности.
        :raises ArgumentsException: Если аргументы некорректны или сущности нет.
        :raises ReferencedEntityException: Если на сущность ссылаются другие сущности.
        """
        entity = self._get(entity_type, entity_id)
        self._ensure_not_referenced(entity)
        collection = self._entity_collections()[entity_type]
        collection.remove(collection.key_of(entity))

    def _get(self, entity_type: EntityType, entity_id: uuid.UUID) -> NamedEntity:
        """Возвращает сущность по типу и коду, а если её нет, бросает исключение.

        :raises ArgumentsException: Если аргументы некорректны или сущности нет.
        """
        entity = self.find(entity_type, entity_id)
        if entity is None:
            raise ArgumentsException("entity_id", f"Сущность {entity_type.value} с кодом {entity_id} не найдена")
        return entity

    def _update(
        self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object], *, merge: bool
    ) -> NamedEntity:
        """Общая часть ``put()`` и ``patch()``: собирает новую сущность из данных и переносит её состояние на месте.

        Новая сущность собирается в стороне, все проверки идут до первого изменения. Затем коллекция
        перестраивается, если ключ уникальности (наименование) изменился: она хранит элемент под ключом,
        вычисленным при добавлении.

        :param merge: True — данные накладываются на текущие поля сущности (patch), False — заменяют их (put).
        :raises ArgumentsException: См. ``put()``.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        target = self._get(entity_type, entity_id)
        fields = CommonValidator.validate_dict(data, "data")
        if merge:
            current = cast(dict[str, object], ConverterFactory().convert(target))
            fields = {**current, **fields}
        else:
            fields = {"id": str(target.id), **fields}

        # Сама сущность не попадает в известные: иначе вместо новой собралась бы она же
        fresh = self._build_entity(entity_type, fields, target)
        collection = self._entity_collections()[entity_type]
        old_key = collection.key_of(target)
        new_key = collection.key_of(fresh)
        if new_key != old_key and collection.has_key(new_key):
            raise ArgumentsException("data", f"Элемент с ключом {new_key!r} уже есть в коллекции")
        if fresh.id != target.id:
            self._ensure_id_is_free(fresh)
            self._ensure_not_referenced(target)

        if new_key != old_key:
            collection.remove(old_key)
        target.replace_state(fresh)
        if new_key != old_key:
            collection.add(target)
        return target

    def _build_entity(self, entity_type: EntityType, data: dict[str, object], exclude: NamedEntity | None) -> NamedEntity:
        """Собирает сущность типа ``entity_type`` из данных; ссылки ``{"id": ...}`` ведут на сущности хранилища.

        Хранилище при этом не меняется.

        :param entity_type: Тип сущности, определяет класс модели.
        :param data: Поля сущности в формате выгрузки; ``model_type`` необязателен.
        :param exclude: Сущность, которую нельзя возвращать по её коду (меняемая): None, если такой нет.
        :return: Новая сущность.
        :raises ArgumentsException: Если данные не словарь, ``model_type`` не тот, ссылка ведёт на неизвестную
            сущность, значения не прошли проверку модели или модель ссылается на то, чего нет в хранилище.
        """
        fields = CommonValidator.validate_dict(data, "data")
        model_class = self._ENTITY_CLASSES[entity_type]
        expected_type = AbstractModel.type_name(model_class)
        if fields.get(AbstractModel.TYPE_FIELD, expected_type) != expected_type:
            raise ArgumentsException(
                AbstractModel.TYPE_FIELD, f"Для типа {entity_type.value} ожидается модель {expected_type}"
            )
        fields = {**fields, AbstractModel.TYPE_FIELD: expected_type}

        factory = DeserializerFactory()
        known = [entity for entity in self._all_entities() if entity is not exclude]
        try:
            with factory.session(known):
                entity = factory.deserialize_as(model_class, fields)
        except OperationException as ex:
            # Для десериализатора это ссылка на неизвестный объект, для вызывающего — некорректные данные
            raise ArgumentsException("data", str(ex)) from ex

        stored = {id(item) for item in self._all_entities()}
        unknown = [str(ref.id) for ref in entity.references() if id(ref) not in stored]
        if unknown:
            raise ArgumentsException("data", f"Ссылки на сущности, которых нет в хранилище: {', '.join(unknown)}")
        return entity

    def _all_entities(self) -> list[NamedEntity]:
        """Возвращает все сущности всех коллекций хранилища."""
        return [entity for collection in self._entity_collections().values() for entity in collection]

    def _ensure_id_is_free(self, entity: NamedEntity) -> None:
        """Проверяет, что код сущности не занят ни одной сущностью хранилища любого типа.

        Коды должны быть уникальны во всём хранилище: ``find_referrers()`` сопоставляет ссылки по коду.

        :raises ArgumentsException: Если код занят.
        """
        if any(stored.id == entity.id for stored in self._all_entities()):
            raise ArgumentsException("id", f"Код {entity.id} уже занят")

    def _ensure_not_referenced(self, entity: NamedEntity) -> None:
        """Проверяет, что на сущность никто не ссылается.

        :raises ReferencedEntityException: Если на сущность ссылаются; в исключении описаны ссылающиеся сущности.
        """
        referrers = self.find_referrers(entity.id)
        if referrers:
            raise ReferencedEntityException(entity.id, [self._describe(referrer) for referrer in referrers])

    def _describe(self, entity: NamedEntity) -> str:
        """Возвращает описание сущности для текста ошибки: тип, наименование и код."""
        for entity_type, collection in self._entity_collections().items():
            if any(item is entity for item in collection):
                return f"{entity_type.value}: {entity.name} ({entity.id})"
        return f"{entity.name} ({entity.id})"

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
