import json
from collections.abc import Callable
from pathlib import Path

import pytest
from Src.Core.named_entity import NamedEntity
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.storage_manager import StorageManager
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel

# Коллекции хранилища
_COLLECTIONS = ("ranges", "nomenclature_groups", "nomenclatures", "warehouses", "recipes")
# Пример выгрузки в репозитории
_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "Docs" / "Examples" / "storage_first_start.json"


def _ref(model: NamedEntity, with_ids: bool) -> tuple[object, ...]:
    """Описывает ссылку на модель: код (если он нужен в сравнении) и наименование."""
    return (model.id if with_ids else None, model.name)


def _range(model: RangeModel, with_ids: bool) -> tuple[object, ...]:
    """Описывает единицу измерения всеми полями вместе с базовой."""
    return (*_ref(model, with_ids), model.factor, model.is_base, _ref(model.base, with_ids))


def _nomenclature(model: NomenclatureModel, with_ids: bool) -> tuple[object, ...]:
    """Описывает номенклатуру всеми полями вместе с группой и единицей."""
    return (
        *_ref(model, with_ids),
        model.full_name,
        _ref(model.group, with_ids),
        _range(model.range, with_ids),
        model.type,
        model.grams_per_base_unit,
    )


def _ingredient(model: IngredientModel, with_ids: bool) -> tuple[object, ...]:
    """Описывает ингредиент всеми полями, включая основание на всю глубину и веса."""
    return (
        _nomenclature(model.nomenclature, with_ids),
        model.quantity,
        model.loss_ratio,
        model.gross_weight,
        model.net_weight,
        tuple(_ingredient(item, with_ids) for item in model.base),
    )


def _recipe(model: RecipeModel, with_ids: bool) -> tuple[object, ...]:
    """Описывает технологическую карту всеми полями вместе с составом и весами."""
    return (
        *_ref(model, with_ids),
        _nomenclature(model.result, with_ids),
        model.output_quantity,
        model.cooking_time_minutes,
        tuple(model.steps),
        tuple(_ingredient(item, with_ids) for item in model.items),
        model.gross_weight,
        model.net_weight,
    )


def _describe(storage: StorageManager, with_ids: bool) -> dict[str, list[tuple[object, ...]]]:
    """Описывает всё хранилище: по каждой коллекции — список описаний её моделей в порядке хранения."""
    return {
        "ranges": [_range(item, with_ids) for item in storage.ranges],
        "nomenclature_groups": [_ref(item, with_ids) for item in storage.nomenclature_groups],
        "nomenclatures": [_nomenclature(item, with_ids) for item in storage.nomenclatures],
        "warehouses": [_ref(item, with_ids) for item in storage.warehouses],
        "recipes": [_recipe(item, with_ids) for item in storage.recipes],
    }


def _export(storage: StorageManager, path: Path) -> str:
    """Выгружает хранилище в JSON-файл так же, как это делает клиент, и возвращает путь к нему."""
    data = ConverterFactory().convert(storage)
    _ = path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def formed(first_start_storage: StorageManager) -> dict[str, list[tuple[object, ...]]]:
    """Описание хранилища, сформированного при первом запуске, снятое до перезагрузки из файла."""
    return _describe(first_start_storage, with_ids=True)


def test_load_file_exported_first_start_equals_formed_storage(
    first_start_storage: StorageManager, formed: dict[str, list[tuple[object, ...]]], tmp_path: Path
):
    """Хранилище, загруженное из собственной выгрузки, совпадает с сформированным: коды, поля, составы и веса."""
    # Подготовка
    file_name = _export(first_start_storage, tmp_path / "storage.json")

    # Действие
    first_start_storage.load(file_name=file_name)

    # Проверка
    assert first_start_storage.is_loaded
    assert _describe(first_start_storage, with_ids=True) == formed


@pytest.mark.parametrize("collection", _COLLECTIONS)
def test_load_file_exported_first_start_keeps_order_and_ids(
    first_start_storage: StorageManager, tmp_path: Path, collection: str
):
    """Каждая коллекция после загрузки хранит те же коды в том же порядке, что и сформированная."""
    # Подготовка
    before = [item.id for item in getattr(first_start_storage, collection)]
    file_name = _export(first_start_storage, tmp_path / "storage.json")

    # Действие
    first_start_storage.load(file_name=file_name)

    # Проверка
    assert before
    assert [item.id for item in getattr(first_start_storage, collection)] == before


def test_load_file_exported_first_start_shares_objects_between_collections(
    first_start_storage: StorageManager, tmp_path: Path
):
    """Модели, которые в файле встречаются много раз, после загрузки — одни и те же объекты, а не копии."""
    # Подготовка
    file_name = _export(first_start_storage, tmp_path / "storage.json")

    # Действие
    first_start_storage.load(file_name=file_name)

    # Проверка
    ranges = first_start_storage.ranges
    groups = first_start_storage.nomenclature_groups
    nomenclatures = first_start_storage.nomenclatures
    assert all(any(item.range is unit for unit in ranges) for item in nomenclatures)
    assert all(any(item.group is group for group in groups) for item in nomenclatures)
    assert all(any(unit.base is other for other in ranges) for unit in ranges)
    for recipe in first_start_storage.recipes:
        assert any(recipe.result is item for item in nomenclatures)
        assert all(any(row.nomenclature is item for item in nomenclatures) for row in recipe.items)


def test_load_file_exported_first_start_find_recipe_works(first_start_storage: StorageManager, tmp_path: Path):
    """После загрузки карта находится по номенклатуре из коллекции хранилища: find_recipe сравнивает по тождеству."""
    # Подготовка
    file_name = _export(first_start_storage, tmp_path / "storage.json")

    # Действие
    first_start_storage.load(file_name=file_name)

    # Проверка
    nomenclatures = {item.id: item for item in first_start_storage.nomenclatures}
    for recipe in first_start_storage.recipes:
        assert first_start_storage.find_recipe(nomenclatures[recipe.result.id]) is recipe


def test_load_file_example_equals_formed_storage_ignoring_ids(
    first_start_storage: StorageManager, load_settings: Callable[..., None]
):
    """Пример выгрузки из Docs/Examples загружается и совпадает с сформированным хранилищем с точностью до кодов."""
    # Подготовка
    formed = _describe(first_start_storage, with_ids=False)

    # Действие
    first_start_storage.load(file_name=str(_EXAMPLE_PATH))

    # Проверка
    assert _describe(first_start_storage, with_ids=False) == formed
