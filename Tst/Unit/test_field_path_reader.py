import pytest
from Src.Core.exception import ArgumentsException
from Src.Logics.field_path_reader import FieldPathReader
from Src.Logics.storage_manager import StorageManager
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.recipe_model import RecipeModel


def get_beef(storage: StorageManager) -> NomenclatureModel:
    """Возвращает номенклатуру «Говядина» из начальных данных."""
    return next(item for item in storage.nomenclatures if item.name == "Говядина")


def get_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает технологическую карту из начальных данных по наименованию."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def test_read_own_field_returns_single_value(first_start_storage: StorageManager):
    """Путь из одного шага возвращает список из одного значения поля самой модели."""
    # Подготовка
    beef = get_beef(first_start_storage)

    # Действие
    result = FieldPathReader().read(beef, "name")

    # Проверка
    assert result == ["Говядина"]


def test_read_unique_code_returns_uuid(first_start_storage: StorageManager):
    """Значение поля возвращается без преобразования: код сущности остаётся UUID."""
    # Подготовка
    beef = get_beef(first_start_storage)

    # Действие
    result = FieldPathReader().read(beef, "id")

    # Проверка
    assert result == [beef.id]


def test_read_nested_path_returns_nested_value(first_start_storage: StorageManager):
    """Путь проходит через вложенные модели: номенклатура, единица измерения, базовая единица."""
    # Подготовка
    beef = get_beef(first_start_storage)

    # Действие
    result = FieldPathReader().read(beef, "range.base.name")

    # Проверка
    assert result == ["грамм"]


def test_read_self_referencing_base_stops_with_path(first_start_storage: StorageManager):
    """Базовая единица ссылается сама на себя, но обход заканчивается вместе с путём."""
    # Подготовка
    beef = get_beef(first_start_storage)

    # Действие
    result = FieldPathReader().read(beef, "range.base.base.base.name")

    # Проверка
    assert result == ["грамм"]


def test_read_path_through_list_returns_value_of_each_item(first_start_storage: StorageManager):
    """Шаг по списку ингредиентов продолжает чтение для каждого элемента в порядке обхода."""
    # Подготовка
    borscht = get_recipe(first_start_storage, "Борщ с говядиной")
    expected = [item.nomenclature.name for item in borscht.items]

    # Действие
    result = FieldPathReader().read(borscht, "items.nomenclature.name")

    # Проверка
    assert result == expected


def test_read_path_through_nested_tuples_returns_flat_values(first_start_storage: StorageManager):
    """Основание ингредиента — кортеж: значения из вложенных коллекций собираются в один плоский список."""
    # Подготовка
    borscht = get_recipe(first_start_storage, "Борщ с говядиной")
    expected = [part.nomenclature.name for item in borscht.items for part in item.base]

    # Действие
    result = FieldPathReader().read(borscht, "items.base.nomenclature.name")

    # Проверка
    assert result == expected
    assert "Говядина (мякоть)" in result


def test_read_empty_collection_returns_empty_list(first_start_storage: StorageManager):
    """У сырья основание пустое, поэтому значений по такому пути нет, и это не ошибка."""
    # Подготовка
    bouillon = get_recipe(first_start_storage, "Бульон костный говяжий")

    # Действие
    result = FieldPathReader().read(bouillon, "items.base.nomenclature.name")

    # Проверка
    assert result == []


def test_read_path_ending_with_list_returns_its_items(first_start_storage: StorageManager):
    """Если путь заканчивается коллекцией, возвращаются её элементы, а не сама коллекция."""
    # Подготовка
    borscht = get_recipe(first_start_storage, "Борщ с говядиной")

    # Действие
    result = FieldPathReader().read(borscht, "steps")

    # Проверка
    assert result == list(borscht.steps)


# Подготовка
@pytest.mark.parametrize(
    "path",
    [
        "_range",
        "__class__",
        "replace_state",
        "range._factor",
        "range.replace_state",
        "unknown",
        "range.unknown",
        "range..name",
    ],
)
def test_read_not_public_property_raises(first_start_storage: StorageManager, path: str):
    """Приватные атрибуты, методы, неизвестные и пустые шаги пути отклоняются ошибкой аргумента."""
    # Подготовка
    beef = get_beef(first_start_storage)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = FieldPathReader().read(beef, path)


def test_read_forbidden_step_after_list_raises(first_start_storage: StorageManager):
    """Шаг после коллекции проверяется у её элементов так же строго, как у обычной модели."""
    # Подготовка
    borscht = get_recipe(first_start_storage, "Борщ с говядиной")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = FieldPathReader().read(borscht, "items._nomenclature")
