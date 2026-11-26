from datetime import datetime
from typing import Self, override

import pytest
from Src.Core.abstract_model import AbstractModel
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Core.unique_collection import UniqueCollection
from Src.Logics.reference_scanner import ReferenceScanner
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.transaction_model import TransactionModel
from Src.Models.warehouse_model import WarehouseModel


def _same_objects(left: list[object], right: list[object]) -> bool:
    """Сравнивает списки по тождеству элементов с учётом порядка."""
    return len(left) == len(right) and all(a is b for a, b in zip(left, right, strict=True))


class _NestedPart(AbstractModel):
    """Вспомогательная вложенная модель без идентификатора для проверки рекурсивного обхода."""

    def __init__(self, target: BaseEntity | None = None) -> None:
        """Инициализирует вложенную модель."""
        self._target: BaseEntity | None = target
        self._self_ref: _NestedPart | None = None
        self._items: list[object] = []

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Заглушка фабричного метода, требуемая контрактом AbstractModel."""
        return cls()


class _CustomEntity(BaseEntity):
    """Вспомогательная сущность без объявления ссылок для проверки сканирования контейнеров и свойств."""

    def __init__(self) -> None:
        """Инициализирует сущность с набором разных контейнеров и необязательным полем."""
        super().__init__()
        self._empty: BaseEntity | None = None
        self._direct: BaseEntity | None = None
        self._as_list: list[object] = []
        self._as_tuple: tuple[object, ...] = ()
        self._as_set: set[object] = set()
        self._as_dict: dict[object, object] = {}
        self._as_unique: UniqueCollection[WarehouseModel] = UniqueCollection(WarehouseModel.name_key)
        self._nested: _NestedPart | None = None
        self._property_calls: int = 0

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Заглушка фабричного метода, требуемая контрактом AbstractModel."""
        return cls()

    @property
    def computed_reference(self) -> BaseEntity | None:
        """Вычисляемое свойство: фиксирует вызов, чтобы проверить, что сканер геттеры не дёргает."""
        self._property_calls += 1
        return self._direct


def test_scan_group_and_warehouse_returns_empty():
    """Группа номенклатуры и склад ни на что не ссылаются."""
    # Подготовка
    scanner = ReferenceScanner()

    # Действие и проверка
    assert scanner.scan(NomenclatureGroupModel.create_meat()) == []
    assert scanner.scan(WarehouseModel.create_restaurant_warehouse()) == []


def test_scan_base_range_excludes_self():
    """Базовая единица ссылается сама на себя, но в результат себя не включает."""
    # Подготовка
    scanner = ReferenceScanner()
    gram = RangeModel("грамм", 1)

    # Действие и проверка
    assert scanner.scan(gram) == []


def test_scan_derived_range_returns_base():
    """Производная единица ссылается на свою базовую единицу."""
    # Подготовка
    scanner = ReferenceScanner()
    kilogram = RangeModel.create_kilogram()

    # Действие
    refs = scanner.scan(kilogram)

    # Проверка
    assert _same_objects(list(refs), [kilogram.base])


def test_scan_nomenclature_returns_only_direct_group_and_range():
    """Номенклатура возвращает группу и единицу измерения, но не базовую единицу внутри производной."""
    # Подготовка
    scanner = ReferenceScanner()
    group = NomenclatureGroupModel.create_meat()
    kilogram = RangeModel.create_kilogram()
    beef = NomenclatureModel.create_raw_material("Говядина", "Говядина охлаждённая", group, kilogram, 1)

    # Действие
    refs = scanner.scan(beef)

    # Проверка
    assert _same_objects(list(refs), [group, kilogram])
    assert all(ref is not kilogram.base for ref in refs)


def test_scan_transaction_returns_direct_nomenclature_warehouse_and_range():
    """Запись журнала возвращает номенклатуру, склад и единицу измерения без транзитивных ссылок."""
    # Подготовка
    scanner = ReferenceScanner()
    group = NomenclatureGroupModel.create_meat()
    kilogram = RangeModel.create_kilogram()
    beef = NomenclatureModel.create_raw_material("Говядина", "Говядина охлаждённая", group, kilogram, 1)
    warehouse = WarehouseModel.create_restaurant_warehouse()
    transaction = TransactionModel(beef, warehouse, kilogram, 5, datetime(2026, 10, 5, 11, 0))

    # Действие
    refs = scanner.scan(transaction)

    # Проверка
    assert _same_objects(list(refs), [beef, warehouse, kilogram])
    assert all(ref is not group and ref is not kilogram.base for ref in refs)


def test_scan_raw_ingredient_returns_nomenclature():
    """Строка состава (AbstractModel без id) без основания ссылается только на свою номенклатуру."""
    # Подготовка
    scanner = ReferenceScanner()
    beef = NomenclatureModel.create_raw_material(
        "Говядина", "Говядина охлаждённая", NomenclatureGroupModel.create_meat(), RangeModel.create_kilogram(), 1
    )

    # Действие
    refs = scanner.scan(IngredientModel(beef, 100))

    # Проверка
    assert _same_objects(list(refs), [beef])


def test_scan_recipe_returns_result_and_nested_ingredient_nomenclatures_without_duplicates(
    first_start_storage: StorageManager,
):
    """Карта возвращает результат и уникальную номенклатуру всех строк и их оснований без групп и единиц."""
    # Подготовка
    scanner = ReferenceScanner()
    borscht = next(recipe for recipe in first_start_storage.recipes if recipe.name == "Борщ с говядиной")
    salt = next(item for item in first_start_storage.nomenclatures if item.name == "Соль")
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")

    # Действие
    refs = scanner.scan(borscht)

    # Проверка
    assert refs[0] is borscht.result
    assert all(isinstance(ref, NomenclatureModel) for ref in refs)
    assert all(any(ref is item.nomenclature for ref in refs) for item in borscht.items)
    assert any(ref is beet for ref in refs)
    assert sum(ref is salt for ref in refs) == 1
    assert len(refs) == len({id(ref) for ref in refs})
    assert len(refs) > len(borscht.items) + 1


def test_scan_custom_model_finds_references_in_all_containers():
    """Новая модель без ручного объявления ссылок сканируется по полям, коллекциям, словарям и вложенным моделям."""
    # Подготовка
    scanner = ReferenceScanner()
    w1, w2, w3 = WarehouseModel("Склад 1"), WarehouseModel("Склад 2"), WarehouseModel("Склад 3")
    w4, w5, w6 = WarehouseModel("Склад 4"), WarehouseModel("Склад 5"), WarehouseModel("Склад 6")
    w7, w8 = WarehouseModel("Склад 7"), WarehouseModel("Склад 8")

    entity = _CustomEntity()
    entity._direct = w1  # pyright: ignore[reportPrivateUsage]
    entity._as_list = [w2, "текст", 42, None]  # pyright: ignore[reportPrivateUsage]
    entity._as_tuple = (w3,)  # pyright: ignore[reportPrivateUsage]
    entity._as_set = {w4}  # pyright: ignore[reportPrivateUsage]
    entity._as_dict = {w5: w6}  # pyright: ignore[reportPrivateUsage]
    entity._as_unique.add(w7)  # pyright: ignore[reportPrivateUsage]
    entity._nested = _NestedPart(w8)  # pyright: ignore[reportPrivateUsage]

    # Действие
    refs = scanner.scan(entity)

    # Проверка
    expected = [w1, w2, w3, w4, w5, w6, w7, w8]
    assert len(refs) == len(expected)
    assert all(any(ref is item for ref in refs) for item in expected)


def test_scan_nested_cycles_do_not_loop_and_still_find_references():
    """Циклы во вложенных моделях, списках и словарях не зацикливают сканер."""
    # Подготовка
    scanner = ReferenceScanner()
    target = WarehouseModel("Склад в цикле")
    part = _NestedPart(target)
    part._self_ref = part  # pyright: ignore[reportPrivateUsage]
    cyclic_list: list[object] = []
    cyclic_list.append(cyclic_list)
    cyclic_list.append(part)
    cyclic_dict: dict[object, object] = {}
    cyclic_dict["self"] = cyclic_dict
    cyclic_dict["part"] = part
    part._items = [cyclic_list, cyclic_dict]  # pyright: ignore[reportPrivateUsage]

    entity = _CustomEntity()
    entity._nested = part  # pyright: ignore[reportPrivateUsage]

    # Действие
    refs = scanner.scan(entity)

    # Проверка
    assert _same_objects(list(refs), [target])


def test_scan_distinct_copies_with_same_uuid_returns_both():
    """Две разные копии сущности с одним UUID не склеиваются: дедупликация идёт по тождеству объекта."""
    # Подготовка
    scanner = ReferenceScanner()
    original = WarehouseModel("Склад")
    copy = WarehouseModel("Склад")
    copy.id = original.id
    entity = _CustomEntity()
    entity._as_list = [original, copy, original]  # pyright: ignore[reportPrivateUsage]

    # Действие
    refs = scanner.scan(entity)

    # Проверка
    assert _same_objects(list(refs), [original, copy])


def test_scan_reads_instance_state_without_calling_properties():
    """Сканер читает состояние экземпляра напрямую и не вызывает геттеры вычисляемых свойств."""
    # Подготовка
    scanner = ReferenceScanner()
    warehouse = WarehouseModel("Склад")
    entity = _CustomEntity()
    entity._direct = warehouse  # pyright: ignore[reportPrivateUsage]

    # Действие
    refs = scanner.scan(entity)

    # Проверка
    assert _same_objects(list(refs), [warehouse])
    assert entity._property_calls == 0  # pyright: ignore[reportPrivateUsage]


# Подготовка
@pytest.mark.parametrize("source", [None, 123, "строка", [], {}])
def test_scan_non_model_raises_arguments_exception(source: object):
    """Объект, не являющийся доменной моделью, отвергается с ArgumentsException."""
    # Подготовка
    scanner = ReferenceScanner()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = scanner.scan(source)  # pyright: ignore[reportArgumentType]
