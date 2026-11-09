import json
from collections.abc import Callable

from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.settings_model import SettingsModel
from Src.Models.warehouse_model import WarehouseModel

# Каждая модель проходит путь «модель -> ConverterFactory -> текст JSON -> DeserializerFactory» отдельно,
# без сессии: так проверяется, что from_dict каждой модели понимает то, что о ней пишет ConverterFactory.
# Загрузку хранилища целиком проверяет test_storage_load_from_file.


def _roundtrip[T](model: T) -> T:
    """Выгружает модель и загружает её обратно, проверяя, что собрана модель того же типа.

    Текст JSON нужен, чтобы данные прошли тот же путь, что и в файле: кортежи становятся списками и т. п.
    """
    data: object = json.loads(json.dumps(ConverterFactory().convert(model), ensure_ascii=False))
    return DeserializerFactory().deserialize_as(type(model), data)


def _ingredient(ingredient: IngredientModel) -> tuple[object, ...]:
    """Приводит ингредиент к кортежу полей, включая основание на всю глубину: у ингредиента нет равенства."""
    return (
        ingredient.nomenclature.id,
        ingredient.quantity,
        ingredient.loss_ratio,
        ingredient.gross_weight,
        ingredient.net_weight,
        tuple(_ingredient(item) for item in ingredient.base),
    )


def test_roundtrip_first_start_ranges_match_stored(first_start_storage: StorageManager):
    """Единицы после выгрузки и загрузки совпадают с исходными, базовая единица снова ссылается сама на себя."""
    for original in first_start_storage.ranges:
        # Действие
        loaded: RangeModel = _roundtrip(original)

        # Проверка
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.factor == original.factor
        assert loaded.is_base == original.is_base
        assert loaded.base == original.base
        if loaded.is_base:
            assert loaded.base is loaded


def test_roundtrip_first_start_groups_match_stored(first_start_storage: StorageManager):
    """Группы после выгрузки и загрузки совпадают с исходными по id и наименованию."""
    for original in first_start_storage.nomenclature_groups:
        # Действие
        loaded: NomenclatureGroupModel = _roundtrip(original)

        # Проверка
        assert loaded == original
        assert loaded.name == original.name


def test_roundtrip_first_start_warehouses_match_stored(first_start_storage: StorageManager):
    """Склады после выгрузки и загрузки совпадают с исходными по id и наименованию."""
    for original in first_start_storage.warehouses:
        # Действие
        loaded: WarehouseModel = _roundtrip(original)

        # Проверка
        assert loaded == original
        assert loaded.name == original.name


def test_roundtrip_first_start_nomenclatures_match_stored(first_start_storage: StorageManager):
    """Номенклатура после выгрузки и загрузки совпадает с исходной по всем полям, вместе с группой и единицей."""
    for original in first_start_storage.nomenclatures:
        # Действие
        loaded: NomenclatureModel = _roundtrip(original)

        # Проверка
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.full_name == original.full_name
        assert loaded.group == original.group
        assert loaded.range == original.range
        assert loaded.range.base == original.range.base
        assert loaded.type is original.type
        assert loaded.grams_per_base_unit == original.grams_per_base_unit


def test_roundtrip_first_start_ingredients_match_stored(first_start_storage: StorageManager):
    """Каждая строка состава каждой карты (в том числе составная) после выгрузки и загрузки совпадает с исходной."""
    for original in (item for recipe in first_start_storage.recipes for item in recipe.items):
        # Действие
        loaded: IngredientModel = _roundtrip(original)

        # Проверка
        assert _ingredient(loaded) == _ingredient(original)


def test_roundtrip_first_start_recipes_match_stored(first_start_storage: StorageManager):
    """Карты после выгрузки и загрузки совпадают с исходными: поля, состав, основание и веса."""
    for original in first_start_storage.recipes:
        # Действие
        loaded: RecipeModel = _roundtrip(original)

        # Проверка
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.result == original.result
        assert loaded.output_quantity == original.output_quantity
        assert loaded.cooking_time_minutes == original.cooking_time_minutes
        assert loaded.steps == original.steps
        assert [_ingredient(item) for item in loaded.items] == [_ingredient(item) for item in original.items]
        assert loaded.gross_weight == original.gross_weight
        assert loaded.net_weight == original.net_weight


def test_roundtrip_settings_match_loaded(load_settings: Callable[..., None]):
    """Настройки вместе с карточкой организации после выгрузки и загрузки совпадают с исходными."""
    # Подготовка
    load_settings(False, "csv")
    original = SettingsManager().settings

    # Действие
    loaded: SettingsModel = _roundtrip(original)

    # Проверка
    assert loaded == original
    assert loaded.boss_name == original.boss_name
    assert loaded.account_name == original.account_name
    assert loaded.is_first_start == original.is_first_start
    assert loaded.response_format is original.response_format
    assert loaded.organization == original.organization
    assert loaded.organization.inn == original.organization.inn
    assert loaded.organization.ownership_form is original.organization.ownership_form
