import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.ingredient_model import IngredientModel
from Src.Models.recipe_model import RecipeModel


def _nomenclature(name: str, nomenclature_id: str | None = None) -> dict[str, object]:
    """Данные номенклатуры-сырья в килограммах."""
    gram = {"id": "5d9c0a62-9f6c-4b6e-8d8b-0a5a1d1f3a01", "name": "грамм"}
    gram.update({"base": {"id": gram["id"]}, "factor": 1})
    return {
        "id": nomenclature_id or str(uuid.uuid4()),
        "name": name,
        "full_name": name,
        "group": {"id": "0b4f6c9e-3b0e-4a39-9d51-4e3a7c3d2b02", "name": "Овощи"},
        "range": {"id": "7c2d8f40-1c55-4e0a-bb0a-9a7b6a1e0c03", "name": "килограмм", "base": gram, "factor": 1000},
        "type": "сырьё",
        "grams_per_base_unit": 1,
    }


def test_deserialize_raw_ingredient_builds_nomenclature_and_defaults():
    """Сырьё без доли потерь и основания собирается с потерями 0 и пустым основанием."""
    # Подготовка
    data = {"nomenclature": _nomenclature("Лук"), "quantity": 200}

    # Действие
    ingredient = DeserializerFactory().deserialize(IngredientModel, data)

    # Проверка
    assert ingredient.nomenclature.name == "Лук"
    assert ingredient.quantity == 200
    assert ingredient.loss_ratio == 0
    assert ingredient.base == ()


def test_deserialize_composite_ingredient_builds_base_recursively():
    """Основание — список ингредиентов: оно собирается тем же десериализатором, на любую глубину."""
    # Подготовка
    onion, carrot, stock = _nomenclature("Лук"), _nomenclature("Морковь"), _nomenclature("Бульон")
    inner = {"nomenclature": carrot, "quantity": 10, "loss_ratio": 0.2, "base": []}
    middle = {"nomenclature": onion, "quantity": 30, "loss_ratio": 0.1, "base": [inner]}
    data = {"nomenclature": stock, "quantity": 100, "loss_ratio": 0.05, "base": [middle]}

    # Действие
    ingredient = DeserializerFactory().deserialize(IngredientModel, data)

    # Проверка
    assert [item.nomenclature.name for item in ingredient.base] == ["Лук"]
    assert [item.nomenclature.name for item in ingredient.base[0].base] == ["Морковь"]
    assert ingredient.base[0].base[0].loss_ratio == 0.2
    # Вес составного узла — вес его основания: 10 базовых единиц по 1 г
    assert ingredient.gross_weight == 10


def test_deserialize_ingredient_ignores_computed_weights():
    """Вычисляемые поля gross_weight и net_weight из файла не читаются: веса считаются заново."""
    # Подготовка
    data = {"nomenclature": _nomenclature("Лук"), "quantity": 200, "gross_weight": 1, "net_weight": 1}

    # Действие
    ingredient = DeserializerFactory().deserialize(IngredientModel, data)

    # Проверка
    assert ingredient.gross_weight == 200


def test_deserialize_ingredients_of_one_nomenclature_share_object():
    """Одна номенклатура в разных ингредиентах — один объект: полный словарь и ссылка дают одно и то же."""
    # Подготовка
    onion = _nomenclature("Лук")
    deserializer = DeserializerFactory().create(IngredientModel)

    # Действие
    first = deserializer.deserialize({"nomenclature": onion, "quantity": 1})
    second = deserializer.deserialize({"nomenclature": {"id": onion["id"]}, "quantity": 2})

    # Проверка
    assert isinstance(first, IngredientModel)
    assert isinstance(second, IngredientModel)
    assert second.nomenclature is first.nomenclature


# Подготовка
@pytest.mark.parametrize("field", ["nomenclature", "quantity"])
def test_deserialize_missing_field_raises(field: str):
    """Отсутствие обязательного поля вызывает ArgumentsException с его именем."""
    # Подготовка
    data = {"nomenclature": _nomenclature("Лук"), "quantity": 200}
    del data[field]

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(IngredientModel, data)
    assert field in str(exc_info.value)


def test_deserialize_base_is_not_a_list_raises():
    """Основание не список — ArgumentsException."""
    # Подготовка
    data = {"nomenclature": _nomenclature("Лук"), "quantity": 200, "base": {"nomenclature": 1}}

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(IngredientModel, data)


def test_deserialize_roundtrip_first_start_ingredients_match_stored(
    first_start_storage, roundtrip: Callable[..., object]
):
    """Каждая строка состава каждой карты (в том числе составная) после выгрузки и загрузки совпадает с исходной."""
    # Подготовка
    recipes: list[RecipeModel] = first_start_storage.recipes

    for original in (item for recipe in recipes for item in recipe.items):
        # Действие
        loaded = roundtrip(original, IngredientModel)

        # Проверка
        assert isinstance(loaded, IngredientModel)
        assert _snapshot(loaded) == _snapshot(original)


def _snapshot(ingredient: IngredientModel) -> tuple[object, ...]:
    """Приводит ингредиент к кортежу полей, включая основание на всю глубину: у ингредиента нет равенства."""
    return (
        ingredient.nomenclature.id,
        ingredient.quantity,
        ingredient.loss_ratio,
        ingredient.gross_weight,
        ingredient.net_weight,
        tuple(_snapshot(item) for item in ingredient.base),
    )
