import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException, OperationException
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.ingredient_model import IngredientModel
from Src.Models.recipe_model import RecipeModel

_PIECE_ID = "7d185d40-a1f7-469c-a070-6f9c924906e1"
_PIECE = {"id": _PIECE_ID, "name": "штука", "base": {"id": _PIECE_ID}, "factor": 1}
_GROUP = {"id": "c394ef96-1f1a-4293-89cd-9df26e0fe80c", "name": "Блюда"}
_SALT_ID = str(uuid.uuid4())
_SOUP_ID = str(uuid.uuid4())


def _salt() -> dict[str, object]:
    """Данные номенклатуры «Соль» (сырьё)."""
    return {
        "id": _SALT_ID, "name": "Соль", "full_name": "Соль", "group": _GROUP, "range": _PIECE,
        "type": "сырьё", "grams_per_base_unit": 1,
    }


def _soup() -> dict[str, object]:
    """Данные номенклатуры «Суп» (блюдо), результата карты."""
    return {
        "id": _SOUP_ID, "name": "Суп", "full_name": "Суп", "group": _GROUP, "range": _PIECE,
        "type": "блюдо", "grams_per_base_unit": 300,
    }


def _recipe(**changes: object) -> dict[str, object]:
    """Данные карты супа с одной строкой состава, поля можно заменить."""
    data: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "name": "Суп",
        "result": _soup(),
        "output_quantity": 1,
        "cooking_time_minutes": 20,
        "steps": ["Сварить", "Посолить"],
        "items": [{"nomenclature": _salt(), "quantity": 5, "loss_ratio": 0, "base": [], "gross_weight": 5}],
        "gross_weight": 5,
        "net_weight": 5,
    }
    data.update(changes)
    return data


def test_deserialize_recipe_builds_result_and_items_recursively():
    """Карта собирает номенклатуру-результат и ингредиенты рекурсивно, шаги и числа берутся из данных."""
    # Подготовка
    data = _recipe()

    # Действие
    recipe = DeserializerFactory().deserialize(RecipeModel, data)

    # Проверка
    assert recipe.name == "Суп"
    assert recipe.result.name == "Суп"
    assert recipe.result.id == uuid.UUID(_SOUP_ID)
    assert recipe.output_quantity == 1
    assert recipe.cooking_time_minutes == 20
    assert recipe.steps == ["Сварить", "Посолить"]
    assert [item.nomenclature.name for item in recipe.items] == ["Соль"]
    assert str(recipe.id) == data["id"]


def test_deserialize_recipe_result_unknown_reference_raises():
    """Результат карты — ссылка на номенклатуру, которой нет в данных: OperationException."""
    # Действие и проверка
    with pytest.raises(OperationException):
        DeserializerFactory().deserialize(RecipeModel, _recipe(result={"id": _SOUP_ID}))


def test_deserialize_recipe_empty_items_builds_empty_recipe():
    """Карта без состава допустима, как и в модели."""
    # Действие
    recipe = DeserializerFactory().deserialize(RecipeModel, _recipe(items=[]))

    # Проверка
    assert recipe.items == []


# Подготовка
@pytest.mark.parametrize("field", ["name", "result", "output_quantity", "cooking_time_minutes", "steps", "items"])
def test_deserialize_missing_field_raises(field: str):
    """Отсутствие любого обязательного поля вызывает ArgumentsException с его именем."""
    # Подготовка
    data = _recipe()
    del data[field]

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(RecipeModel, data)
    assert field in str(exc_info.value)


def test_deserialize_recipe_result_not_cookable_raises():
    """Правила модели действуют и при загрузке: результатом карты не может быть сырьё."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(RecipeModel, _recipe(result=_salt()))


def test_deserialize_recipe_items_not_a_list_raises():
    """Состав не список — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(RecipeModel, _recipe(items="Соль"))


def test_deserialize_roundtrip_first_start_recipes_match_stored(first_start_storage, roundtrip: Callable[..., object]):
    """Все карты хранилища после выгрузки и загрузки совпадают с исходными: поля, состав, основание и веса."""
    for original in first_start_storage.recipes:
        # Действие
        loaded = roundtrip(original, RecipeModel)

        # Проверка
        assert isinstance(loaded, RecipeModel)
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.result == original.result
        assert loaded.output_quantity == original.output_quantity
        assert loaded.cooking_time_minutes == original.cooking_time_minutes
        assert loaded.steps == original.steps
        assert [_snapshot(item) for item in loaded.items] == [_snapshot(item) for item in original.items]
        assert loaded.gross_weight == original.gross_weight
        assert loaded.net_weight == original.net_weight


def _snapshot(ingredient: IngredientModel) -> tuple[object, ...]:
    """Приводит ингредиент к кортежу полей, включая основание на всю глубину: у ингредиента нет равенства."""
    return (
        ingredient.nomenclature.id,
        ingredient.quantity,
        ingredient.loss_ratio,
        tuple(_snapshot(item) for item in ingredient.base),
    )
