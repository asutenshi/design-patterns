import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.named_entity import NamedEntity
from Src.Models.nomenclature_group_model import NomenclatureGroupModel

# Проверки наименования и идентификатора (пробелы, пустые и не строковые значения,
# уникальность id) написаны один раз для NamedEntity и BaseEntity: см. test_named_entity,
# test_entities и test_inheritance_contracts.


def test_init_valid_name_created():
    """Группа номенклатуры создаётся с переданным наименованием и заданным идентификатором."""
    # Подготовка
    name = "Сырьё"

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name
    assert group.id is not None


def test_init_any_instance_is_named_entity():
    """Группа номенклатуры является наследником NamedEntity и получает от него наименование."""
    # Подготовка
    group = NomenclatureGroupModel("Сырьё")

    # Действие
    result = isinstance(group, NamedEntity)

    # Проверка
    assert result is True


def test_init_long_name_created():
    """Для группы ограничение в 50 символов не действует."""
    # Подготовка
    name = "a" * 100

    # Действие
    group = NomenclatureGroupModel(name)

    # Проверка
    assert group.name == name


# Подготовка
@pytest.mark.parametrize(
    ("factory", "expected_name"),
    [
        (NomenclatureGroupModel.create_meat, "Мясные продукты"),
        (NomenclatureGroupModel.create_dairy, "Молочные продукты"),
        (NomenclatureGroupModel.create_vegetables, "Овощи"),
        (NomenclatureGroupModel.create_grocery, "Бакалея"),
        (NomenclatureGroupModel.create_semi_finished, "Полуфабрикаты"),
        (NomenclatureGroupModel.create_dishes, "Блюда"),
        (NomenclatureGroupModel.create_packaging, "Упаковка"),
    ],
    ids=lambda value: value.__name__ if callable(value) else value,
)
def test_create_group_returns_group_with_expected_name(factory, expected_name):
    """Фабрика создаёт группу с ожидаемым наименованием, каждый вызов — новый объект."""
    # Действие
    first = factory()
    second = factory()

    # Проверка
    assert isinstance(first, NomenclatureGroupModel)
    assert first.name == expected_name
    assert first is not second


# ---------------------------------------------------------------------------
# from_dict: создание из словаря полей, как его записал ConverterFactory
# ---------------------------------------------------------------------------


def test_from_dict_valid_name_fields_set():
    """Группа создаётся из словаря по наименованию, служебные поля model_type и id не читаются."""
    # Подготовка
    data: dict[str, object] = {
        "model_type": "Src.Models.nomenclature_group_model.NomenclatureGroupModel",
        "id": "7d185d40-a1f7-469c-a070-6f9c924906e1",
        "name": "Овощи",
    }

    # Действие
    model = NomenclatureGroupModel.from_dict(data)

    # Проверка
    assert model.name == "Овощи"
    assert str(model.id) != data["id"]


def test_from_dict_missing_name_raises():
    """Без наименования модель не создаётся: ArgumentsException с именем поля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        NomenclatureGroupModel.from_dict({"title": "Овощи"})
    assert "name" in str(exc_info.value)


def test_from_dict_empty_name_raises():
    """Правила конструктора действуют и в from_dict: пустое наименование недопустимо."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NomenclatureGroupModel.from_dict({"name": "  "})
