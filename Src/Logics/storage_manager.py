from typing import Any, override

from Src.Core.abstract_manager import AbstractManager
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
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

    Начальные данные формируются здесь же, в приватном методе. Когда их станет много
    (рецепты, рестораны, сотрудники), их стоит вынести в отдельный класс.
    """

    # Единицы измерения
    _ranges: UniqueCollection[RangeModel]
    # Группы номенклатуры
    _nomenclature_groups: UniqueCollection[NomenclatureGroupModel]
    # Номенклатура
    _nomenclatures: UniqueCollection[NomenclatureModel]
    # Склады
    _warehouses: UniqueCollection[WarehouseModel]

    @override
    def _initialize(self) -> None:
        """Создаёт пустые коллекции сущностей.

        Метод вызывается и при создании экземпляра, и в convert() для сброса состояния.
        """
        self._ranges = UniqueCollection(_name_key)
        self._nomenclature_groups = UniqueCollection(_name_key)
        self._nomenclatures = UniqueCollection(_name_key)
        self._warehouses = UniqueCollection(_name_key)

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        """Возвращает пустые данные: внешнего источника пока нет.

        Сюда придёт чтение из SQLite.

        :param file_name: Не используется.
        :return: Пустой словарь.
        """
        return {}

    @override
    def convert(self) -> None:
        """Пересоздаёт коллекции и при первом запуске наполняет их начальными данными.

        :raises OperationException: Если настройки не загружены или начальные данные
            содержат дубликаты.
        """
        # Обращение к настройкам здесь, а не в _initialize: хук не должен зависеть от других менеджеров
        is_first_start = SettingsManager().settings.is_first_start

        self._initialize()
        if not is_first_start:
            return

        try:
            self._fill_first_start_data()
        except ArgumentsException as ex:
            self._initialize()
            raise OperationException(f"Не удалось сформировать начальные данные: {ex}") from ex

    def _fill_first_start_data(self) -> None:
        """Наполняет коллекции начальными данными.

        Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях:
        каждый объект создаётся один раз и добавляется в коллекцию.

        :raises ArgumentsException: Если начальные данные содержат дубликаты.
        """
        gram = RangeModel("грамм", 1)
        kilogram = RangeModel("килограмм", 1000, gram)
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
            NomenclatureModel("Говядина", "Говядина охлаждённая", meat, kilogram),
            NomenclatureModel("Молоко", "Молоко пастеризованное 3,2%", dairy, liter),
            NomenclatureModel("Стакан", "Стакан бумажный 300 мл", packaging, piece),
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
