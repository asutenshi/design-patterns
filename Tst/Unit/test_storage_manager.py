import json
from collections.abc import Callable
from pathlib import Path

import pytest
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.recipe_model import RecipeModel

# Начальные данные, которые создаются при первом запуске
EXPECTED_RANGES = ["грамм", "килограмм", "миллилитр", "литр", "штука"]
EXPECTED_GROUPS = [
    "Мясные продукты",
    "Молочные продукты",
    "Овощи",
    "Бакалея",
    "Полуфабрикаты",
    "Блюда",
    "Упаковка",
]
EXPECTED_NOMENCLATURES = [
    "Говядина",
    "Молоко",
    "Стакан",
    "Кости говяжьи мозговые",
    "Говядина (мякоть)",
    "Лук репчатый",
    "Морковь",
    "Свёкла",
    "Картофель",
    "Капуста белокочанная",
    "Укроп",
    "Лавровый лист",
    "Перец чёрный горошком",
    "Соль",
    "Томатная паста",
    "Масло подсолнечное",
    "Уксус 9%",
    "Сахар",
    "Сметана 20%",
    "Контейнер для супа 500 мл",
    "Бульон костный говяжий",
    "Говядина отварная",
    "Зажарка свекольная",
    "Борщ с говядиной",
]
EXPECTED_WAREHOUSES = ["Склад ресторана", "Склад производственного цеха"]
EXPECTED_RECIPES = ["Бульон костный говяжий", "Говядина отварная", "Зажарка свекольная", "Борщ с говядиной"]


@pytest.fixture
def load_settings(tmp_path: Path) -> Callable[[bool], None]:
    """Возвращает функцию, которая загружает в SettingsManager настройки с заданным флагом первого запуска."""

    def load(is_first_start: bool) -> None:
        data = {
            "organization": {
                "name": "Ромашка",
                "inn": "1234567894",
                "bic": "123456789",
                "account": "12345678901234567890",
                "ownership_form": "ООО",
            },
            "boss_name": "Иванов Иван Иванович",
            "account_name": "Петрова Анна Александровна",
            "is_first_start": is_first_start,
        }
        path = tmp_path / "settings.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        SettingsManager().load(str(path))

    return load


@pytest.fixture
def first_start_storage(load_settings: Callable[[bool], None]) -> StorageManager:
    """Хранилище, загруженное при первом запуске."""
    load_settings(True)
    storage = StorageManager()
    storage.load()
    return storage


# ---------------------------------------------------------------------------
# До загрузки и ошибки
# ---------------------------------------------------------------------------


def test_properties_before_load_are_empty():
    """До load() все коллекции пусты."""
    # Подготовка
    storage = StorageManager()

    # Действие
    collections = [
        storage.ranges,
        storage.nomenclature_groups,
        storage.nomenclatures,
        storage.warehouses,
        storage.recipes,
    ]

    # Проверка
    assert collections == [[], [], [], [], []]


def test_load_settings_not_loaded_raises_operation_exception():
    """Без загруженных настроек load() бросает OperationException."""
    # Подготовка
    storage = StorageManager()

    # Действие и проверка
    with pytest.raises(OperationException):
        storage.load()
    assert storage.is_loaded is False
    assert storage.ranges == []


# ---------------------------------------------------------------------------
# Первый запуск
# ---------------------------------------------------------------------------


def test_load_first_start_creates_ranges(first_start_storage: StorageManager):
    """При первом запуске создаются единицы измерения."""
    # Действие
    names = [item.name for item in first_start_storage.ranges]

    # Проверка
    assert names == EXPECTED_RANGES


def test_load_first_start_creates_nomenclature_groups(first_start_storage: StorageManager):
    """При первом запуске создаются группы номенклатуры."""
    # Действие
    names = [item.name for item in first_start_storage.nomenclature_groups]

    # Проверка
    assert names == EXPECTED_GROUPS


def test_load_first_start_creates_nomenclatures(first_start_storage: StorageManager):
    """При первом запуске создаётся номенклатура."""
    # Действие
    names = [item.name for item in first_start_storage.nomenclatures]

    # Проверка
    assert names == EXPECTED_NOMENCLATURES


# Подготовка
@pytest.mark.parametrize(
    ("nomenclature_name", "expected_type", "expected_grams_per_base_unit"),
    [
        ("Говядина", NomenclatureType.RAW_MATERIAL, 1),
        ("Молоко", NomenclatureType.RAW_MATERIAL, 1),
        ("Стакан", NomenclatureType.PACKAGING, 10),
        ("Лавровый лист", NomenclatureType.RAW_MATERIAL, 0.5),
        ("Масло подсолнечное", NomenclatureType.RAW_MATERIAL, 0.92),
        ("Контейнер для супа 500 мл", NomenclatureType.PACKAGING, 20),
        ("Бульон костный говяжий", NomenclatureType.SEMI_FINISHED, 1),
        ("Зажарка свекольная", NomenclatureType.SEMI_FINISHED, 1),
        ("Борщ с говядиной", NomenclatureType.DISH, 500),
    ],
)
def test_load_first_start_nomenclature_has_type_and_weight(
    first_start_storage: StorageManager,
    nomenclature_name: str,
    expected_type: NomenclatureType,
    expected_grams_per_base_unit: float,
):
    """Начальная номенклатура создаётся с ожидаемым типом позиции и весом базовой единицы."""
    # Подготовка
    nomenclatures = {item.name: item for item in first_start_storage.nomenclatures}

    # Действие
    nomenclature = nomenclatures[nomenclature_name]

    # Проверка
    assert nomenclature.type is expected_type
    assert nomenclature.grams_per_base_unit == expected_grams_per_base_unit


def test_load_first_start_creates_warehouses(first_start_storage: StorageManager):
    """При первом запуске создаются склады."""
    # Действие
    names = [item.name for item in first_start_storage.warehouses]

    # Проверка
    assert names == EXPECTED_WAREHOUSES


def test_load_first_start_derived_range_references_stored_base(first_start_storage: StorageManager):
    """Производная единица ссылается на ту же базовую, что лежит в коллекции."""
    # Подготовка
    ranges = {item.name: item for item in first_start_storage.ranges}

    # Действие и проверка
    assert ranges["килограмм"].base is ranges["грамм"]
    assert ranges["литр"].base is ranges["миллилитр"]
    assert ranges["килограмм"].factor == 1000
    assert ranges["литр"].factor == 1000


def test_load_first_start_nomenclature_references_stored_range_and_group(first_start_storage: StorageManager):
    """Номенклатура хранит те же объекты единицы и группы, что лежат в коллекциях, а не копии."""
    # Подготовка
    ranges = first_start_storage.ranges
    groups = first_start_storage.nomenclature_groups

    # Действие и проверка
    for nomenclature in first_start_storage.nomenclatures:
        assert any(nomenclature.range is item for item in ranges)
        assert any(nomenclature.group is item for item in groups)


# Подготовка
@pytest.mark.parametrize(
    ("nomenclature_name", "group_name", "range_name", "base_range_name"),
    [
        ("Говядина", "Мясные продукты", "килограмм", "грамм"),
        ("Молоко", "Молочные продукты", "литр", "миллилитр"),
        ("Стакан", "Упаковка", "штука", "штука"),
        ("Свёкла", "Овощи", "килограмм", "грамм"),
        ("Масло подсолнечное", "Бакалея", "литр", "миллилитр"),
        ("Сметана 20%", "Молочные продукты", "килограмм", "грамм"),
        ("Контейнер для супа 500 мл", "Упаковка", "штука", "штука"),
        ("Бульон костный говяжий", "Полуфабрикаты", "литр", "миллилитр"),
        ("Говядина отварная", "Полуфабрикаты", "килограмм", "грамм"),
        ("Борщ с говядиной", "Блюда", "штука", "штука"),
    ],
)
def test_load_first_start_nomenclature_uses_its_own_stored_group_and_range(
    first_start_storage: StorageManager,
    nomenclature_name: str,
    group_name: str,
    range_name: str,
    base_range_name: str,
):
    """Номенклатура ссылается на свою группу и свою единицу из коллекций (те же объекты, не копии).

    Для говядины это группа «Мясные продукты» и килограмм, а база килограмма — тот же грамм,
    что лежит в коллекции единиц.
    """
    # Подготовка
    nomenclatures = {item.name: item for item in first_start_storage.nomenclatures}
    groups = {item.name: item for item in first_start_storage.nomenclature_groups}
    ranges = {item.name: item for item in first_start_storage.ranges}

    # Действие
    nomenclature = nomenclatures[nomenclature_name]

    # Проверка
    assert nomenclature.group is groups[group_name]
    assert nomenclature.range is ranges[range_name]
    assert nomenclature.range.base is ranges[base_range_name]


# Подготовка
@pytest.mark.parametrize(
    "collection", ["ranges", "nomenclature_groups", "nomenclatures", "warehouses", "recipes"]
)
def test_load_first_start_elements_are_unique_by_id_and_name(first_start_storage: StorageManager, collection: str):
    """В каждой коллекции нет повторяющихся идентификаторов и наименований."""
    # Подготовка
    items = getattr(first_start_storage, collection)

    # Действие
    ids = [item.id for item in items]
    names = [item.name.casefold() for item in items]

    # Проверка
    assert len(items) > 0
    assert len(set(ids)) == len(ids)
    assert len(set(names)) == len(names)


def test_load_first_start_ids_are_unique_across_all_collections(first_start_storage: StorageManager):
    """Идентификаторы не повторяются и между коллекциями."""
    # Подготовка
    items = [
        *first_start_storage.ranges,
        *first_start_storage.nomenclature_groups,
        *first_start_storage.nomenclatures,
        *first_start_storage.warehouses,
        *first_start_storage.recipes,
    ]

    # Действие
    ids = [item.id for item in items]

    # Проверка
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------------
# Технологические карты
# ---------------------------------------------------------------------------


def make_cycle_nomenclatures(storage: StorageManager, count: int) -> list[NomenclatureModel]:
    """Создаёт полуфабрикаты с группой и единицей из хранилища, которых нет в начальных данных."""
    group = storage.nomenclature_groups[0]
    unit = storage.ranges[0]
    return [
        NomenclatureModel.create_semi_finished(f"Цикл {index}", f"Цикл {index} (полное)", group, unit, 1)
        for index in range(count)
    ]


def make_inclusion_recipe(result: NomenclatureModel, ingredient: NomenclatureModel) -> RecipeModel:
    """Создаёт карту результата, в состав которой входит одна номенклатура."""
    return RecipeModel(result.name, result, 1, 1, ["Смешать"], [IngredientModel(ingredient, 1)])


def test_load_first_start_creates_recipes(first_start_storage: StorageManager):
    """При первом запуске создаются четыре карты из Recipes.md в порядке регистрации."""
    # Действие
    names = [recipe.name for recipe in first_start_storage.recipes]

    # Проверка
    assert names == EXPECTED_RECIPES


def test_load_first_start_recipe_results_are_stored_nomenclature(first_start_storage: StorageManager):
    """Результат и ингредиенты карты — те же объекты, что лежат в коллекции номенклатуры, а не копии."""
    # Подготовка
    nomenclatures = first_start_storage.nomenclatures

    # Действие и проверка
    for recipe in first_start_storage.recipes:
        assert any(recipe.result is item for item in nomenclatures)
        for ingredient in recipe.ingredients:
            assert any(ingredient.nomenclature is item for item in nomenclatures)


def test_load_first_start_every_semi_finished_ingredient_has_recipe(first_start_storage: StorageManager):
    """У каждого полуфабриката в составе любой карты есть собственная карта."""
    # Подготовка
    ingredients = [ingredient for recipe in first_start_storage.recipes for ingredient in recipe.ingredients]
    semi_finished = [i.nomenclature for i in ingredients if i.nomenclature.type is NomenclatureType.SEMI_FINISHED]

    # Действие и проверка
    assert len(semi_finished) > 0
    for nomenclature in semi_finished:
        assert first_start_storage.find_recipe(nomenclature) is not None


def test_load_first_start_recipe_results_have_allowed_types(first_start_storage: StorageManager):
    """Полуфабрикатам и блюду соответствуют типы SEMI_FINISHED и DISH."""
    # Действие
    types = {recipe.name: recipe.result.type for recipe in first_start_storage.recipes}

    # Проверка
    assert types == {
        "Бульон костный говяжий": NomenclatureType.SEMI_FINISHED,
        "Говядина отварная": NomenclatureType.SEMI_FINISHED,
        "Зажарка свекольная": NomenclatureType.SEMI_FINISHED,
        "Борщ с говядиной": NomenclatureType.DISH,
    }


def test_find_recipe_semi_finished_returns_its_recipe(first_start_storage: StorageManager):
    """Карта полуфабриката находится по номенклатуре-результату."""
    # Подготовка
    nomenclatures = {item.name: item for item in first_start_storage.nomenclatures}
    bouillon = nomenclatures["Бульон костный говяжий"]

    # Действие
    recipe = first_start_storage.find_recipe(bouillon)

    # Проверка
    assert recipe is not None
    assert recipe.result is bouillon
    assert recipe.name == "Бульон костный говяжий"


def test_find_recipe_raw_material_returns_none(first_start_storage: StorageManager):
    """У сырья карты нет."""
    # Подготовка
    nomenclatures = {item.name: item for item in first_start_storage.nomenclatures}

    # Действие и проверка
    assert first_start_storage.find_recipe(nomenclatures["Картофель"]) is None


def test_recipes_returned_list_modification_does_not_change_storage(first_start_storage: StorageManager):
    """Изменение возвращённого списка карт не меняет коллекцию в хранилище."""
    # Подготовка
    recipes = first_start_storage.recipes

    # Действие
    recipes.clear()

    # Проверка
    assert len(first_start_storage.recipes) == len(EXPECTED_RECIPES)


def test_add_recipe_second_recipe_for_same_result_raises(first_start_storage: StorageManager):
    """На одну номенклатуру-результат допускается одна карта."""
    # Подготовка
    existing = first_start_storage.recipes[0]
    duplicate = make_inclusion_recipe(existing.result, first_start_storage.nomenclatures[0])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        first_start_storage._add_recipe(duplicate)  # pyright: ignore[reportPrivateUsage]
    assert len(first_start_storage.recipes) == len(EXPECTED_RECIPES)


# Подготовка
@pytest.mark.parametrize("chain_length", [2, 3])
def test_add_recipe_cycle_through_several_recipes_raises(first_start_storage: StorageManager, chain_length: int):
    """Цикл через несколько карт отвергается при регистрации замыкающей карты, и она не добавляется."""
    # Подготовка
    items = make_cycle_nomenclatures(first_start_storage, chain_length)
    recipes = [make_inclusion_recipe(items[i], items[(i + 1) % chain_length]) for i in range(chain_length)]
    for recipe in recipes[:-1]:
        first_start_storage._add_recipe(recipe)  # pyright: ignore[reportPrivateUsage]
    count_before = len(first_start_storage.recipes)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        first_start_storage._add_recipe(recipes[-1])  # pyright: ignore[reportPrivateUsage]
    assert len(first_start_storage.recipes) == count_before
    assert first_start_storage.find_recipe(items[-1]) is None


def test_add_recipe_chain_without_cycle_allowed(first_start_storage: StorageManager):
    """Цепочка включений A включает B, B включает C без возврата допускается."""
    # Подготовка
    first, second, third = make_cycle_nomenclatures(first_start_storage, 3)

    # Действие
    first_start_storage._add_recipe(make_inclusion_recipe(second, third))  # pyright: ignore[reportPrivateUsage]
    first_start_storage._add_recipe(make_inclusion_recipe(first, second))  # pyright: ignore[reportPrivateUsage]

    # Проверка
    assert first_start_storage.find_recipe(first) is not None
    assert first_start_storage.find_recipe(second) is not None


# ---------------------------------------------------------------------------
# Не первый запуск и повторная загрузка
# ---------------------------------------------------------------------------


def test_load_not_first_start_collections_stay_empty(load_settings: Callable[[bool], None]):
    """Если запуск не первый, начальные данные не создаются."""
    # Подготовка
    load_settings(False)
    storage = StorageManager()

    # Действие
    storage.load()

    # Проверка
    assert storage.ranges == []
    assert storage.nomenclature_groups == []
    assert storage.nomenclatures == []
    assert storage.warehouses == []
    assert storage.recipes == []


def test_load_repeated_first_start_does_not_duplicate_elements(first_start_storage: StorageManager):
    """Повторная загрузка пересоздаёт данные, а не дописывает их к прежним."""
    # Действие
    first_start_storage.load()

    # Проверка
    assert len(first_start_storage.ranges) == len(EXPECTED_RANGES)
    assert len(first_start_storage.nomenclature_groups) == len(EXPECTED_GROUPS)
    assert len(first_start_storage.nomenclatures) == len(EXPECTED_NOMENCLATURES)
    assert len(first_start_storage.warehouses) == len(EXPECTED_WAREHOUSES)
    assert len(first_start_storage.recipes) == len(EXPECTED_RECIPES)


def test_load_repeated_after_first_start_flag_off_clears_collections(
    first_start_storage: StorageManager, load_settings: Callable[[bool], None]
):
    """Если после первого запуска флаг сброшен, повторная загрузка очищает коллекции."""
    # Подготовка
    load_settings(False)

    # Действие
    first_start_storage.load()

    # Проверка
    assert first_start_storage.ranges == []
    assert first_start_storage.warehouses == []
    assert first_start_storage.recipes == []


def test_load_settings_reload_fails_raises_and_is_loaded_becomes_false(
    first_start_storage: StorageManager, tmp_path: Path
):
    """Если настройки не удалось перечитать, повторная загрузка хранилища падает и сбрасывает is_loaded."""
    # Подготовка
    broken = tmp_path / "broken.json"
    broken.write_text("{}", encoding="utf-8")
    with pytest.raises(OperationException):
        SettingsManager().load(str(broken))

    # Действие и проверка
    with pytest.raises(OperationException):
        first_start_storage.load()
    assert first_start_storage.is_loaded is False


class OtherSettingsManager(SettingsManager):
    """Менеджер настроек-заглушка: наследник с собственным экземпляром, независимым от SettingsManager."""


def _load_other_settings(tmp_path: Path, is_first_start: bool) -> OtherSettingsManager:
    """Загружает в независимый менеджер настроек файл с заданным флагом первого запуска."""
    data = SettingsManager._default_data()  # pyright: ignore[reportPrivateUsage]
    data["is_first_start"] = is_first_start
    path = tmp_path / "other.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    other = OtherSettingsManager()
    other.load(str(path))
    return other


def test_load_explicit_settings_manager_is_used_instead_of_singleton(
    load_settings: Callable[[bool], None], tmp_path: Path
):
    """Переданный менеджер настроек используется вместо единственного экземпляра SettingsManager."""
    # Подготовка
    load_settings(True)
    other = _load_other_settings(tmp_path, is_first_start=False)
    storage = StorageManager()

    # Действие
    storage.load(other)

    # Проверка
    assert storage.is_loaded is True
    assert storage.ranges == []


def test_load_explicit_settings_manager_first_start_fills_collections(
    load_settings: Callable[[bool], None], tmp_path: Path
):
    """Флаг первого запуска берётся из переданного менеджера, а не из SettingsManager."""
    # Подготовка
    load_settings(False)
    other = _load_other_settings(tmp_path, is_first_start=True)
    storage = StorageManager()

    # Действие
    storage.load(other)

    # Проверка
    assert [unit.name for unit in storage.ranges] == EXPECTED_RANGES


def test_load_explicit_settings_manager_not_loaded_raises_operation_exception(
    load_settings: Callable[[bool], None],
):
    """Если переданный менеджер не загружен, бросается OperationException, даже когда SettingsManager загружен."""
    # Подготовка
    load_settings(True)
    storage = StorageManager()

    # Действие и проверка
    with pytest.raises(OperationException):
        storage.load(OtherSettingsManager())
    assert storage.is_loaded is False


# ---------------------------------------------------------------------------
# Защита от изменения снаружи
# ---------------------------------------------------------------------------


def test_properties_returned_list_modification_does_not_change_storage(first_start_storage: StorageManager):
    """Изменение возвращённого списка не меняет коллекцию в хранилище."""
    # Подготовка
    ranges = first_start_storage.ranges

    # Действие
    ranges.clear()

    # Проверка
    assert len(first_start_storage.ranges) == len(EXPECTED_RANGES)