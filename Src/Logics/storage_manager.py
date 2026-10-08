from typing import ClassVar, Self, cast, override

from Src.Core.abstract_manager import AbstractManager
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
from Src.Core.nomenclature_type import NomenclatureType
from Src.Core.unique_collection import UniqueCollection
from Src.Logics.settings_manager import SettingsManager
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.warehouse_model import WarehouseModel


def _name_key(entity: NamedEntity) -> str:
    """Возвращает ключ уникальности по наименованию без учёта регистра."""
    return entity.name.casefold()


class StorageManager(AbstractManager):
    """Хранилище коллекций доменных моделей (Singleton).

    Каждая коллекция не содержит дубликатов по наименованию (без учёта регистра).
    При первом запуске (флаг ``is_first_start`` в настройках) ``load()`` наполняет
    коллекции начальными данными. Иначе коллекции остаются пустыми: загружать
    данные пока неоткуда, чтение из БД появится вместе с SQLite.

    Хранилище зависит от менеджера настроек: ``load()`` принимает его параметром,
    по умолчанию берёт единственный экземпляр SettingsManager. Настройки должны быть
    загружены заранее, сам ``load()`` их не загружает.

    Начальные данные формируются здесь же, в приватном методе. Когда их станет много
    (рецепты, рестораны, сотрудники), их стоит вынести в отдельный класс.
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

        Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях:
        каждый объект создаётся один раз и добавляется в коллекцию.

        :raises ArgumentsException: Если начальные данные содержат дубликаты.
        """
        kilogram = RangeModel.create_kilogram()
        gram = kilogram.base
        milliliter = RangeModel("миллилитр", 1)
        liter = RangeModel("литр", 1000, milliliter)
        piece = RangeModel("штука", 1)
        for unit in (gram, kilogram, milliliter, liter, piece):
            self._ranges.add(unit)

        meat = NomenclatureGroupModel("Мясные продукты")
        dairy = NomenclatureGroupModel("Молочные продукты")
        packaging = NomenclatureGroupModel("Упаковка")
        for group in (meat, dairy, packaging):
            self._nomenclature_groups.add(group)

        for nomenclature in (
            NomenclatureModel("Говядина", "Говядина охлаждённая", meat, kilogram, NomenclatureType.RAW_MATERIAL, 1),
            # Плотность молока принята за 1 г/мл
            NomenclatureModel("Молоко", "Молоко пастеризованное 3,2%", dairy, liter, NomenclatureType.RAW_MATERIAL, 1),
            NomenclatureModel("Стакан", "Стакан бумажный 300 мл", packaging, piece, NomenclatureType.PACKAGING, 10),
        ):
            self._nomenclatures.add(nomenclature)

        for warehouse in (
            WarehouseModel("Склад ресторана"),
            WarehouseModel("Склад производственного цеха"),
        ):
            self._warehouses.add(warehouse)

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
