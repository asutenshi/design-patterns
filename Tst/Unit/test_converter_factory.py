import json
import uuid
from datetime import UTC, date, datetime

import pytest
from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.basic_converter import BasicConverter
from Src.Logics.collection_converter import CollectionConverter
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.datetime_converter import DatetimeConverter
from Src.Logics.reference_converter import ReferenceConverter
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


class _Event:
    """Тестовая модель с датами: в доменных моделях дат пока нет."""

    _title: str
    _created_at: datetime
    _dates: list[date]

    def __init__(self, title: str, created_at: datetime, dates: list[date]) -> None:
        """Инициализирует событие."""
        self._title = title
        self._created_at = created_at
        self._dates = dates

    @property
    def title(self) -> str:
        """Возвращает наименование события."""
        return self._title

    @property
    def created_at(self) -> datetime:
        """Возвращает момент создания события."""
        return self._created_at

    @property
    def dates(self) -> list[date]:
        """Возвращает даты проведения события."""
        return self._dates


class _Pair:
    """Тестовая модель с двумя ссылками: для проверки общих объектов и циклов."""

    _first: object
    _second: object

    def __init__(self, first: object, second: object) -> None:
        """Инициализирует пару."""
        self._first = first
        self._second = second

    @property
    def first(self) -> object:
        """Возвращает первый элемент пары."""
        return self._first

    @property
    def second(self) -> object:
        """Возвращает второй элемент пары."""
        return self._second


def _group_dict(group: NomenclatureGroupModel) -> dict[str, object]:
    """Возвращает ожидаемый словарь группы."""
    return {"id": str(group.id), "name": group.name}


def _base_range_dict(unit: RangeModel) -> dict[str, object]:
    """Возвращает ожидаемый словарь базовой единицы: её base замыкает цикл и записывается ссылкой."""
    return {"id": str(unit.id), "name": unit.name, "base": {"id": str(unit.id)}, "factor": 1, "is_base": True}


def _raw_material(name: str, group: NomenclatureGroupModel, unit: RangeModel) -> NomenclatureModel:
    """Создаёт сырьё с весом базовой единицы 1 г."""
    return NomenclatureModel.create_raw_material(name, f"{name} полностью", group, unit, 1)


# ---------------------------------------------------------------------------
# create(): выбор конвертера по типу значения
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize(
    ("value", "converter_type"),
    [
        ("Мука", BasicConverter),
        (1, BasicConverter),
        (1.5, BasicConverter),
        (True, BasicConverter),
        (None, BasicConverter),
        (NomenclatureType.DISH, BasicConverter),
        (uuid.uuid4(), BasicConverter),
        (datetime(2026, 10, 22, 12, 30, tzinfo=UTC), DatetimeConverter),
        (date(2026, 10, 22), DatetimeConverter),
        (["Мука"], CollectionConverter),
        (("Мука",), CollectionConverter),
        (NomenclatureGroupModel("Мясо"), ReferenceConverter),
        (RangeModel.create_piece(), ReferenceConverter),
        (_Pair(1, 2), ReferenceConverter),
    ],
    ids=[
        "str", "int", "float", "bool", "none", "enum", "uuid", "datetime", "date",
        "list", "tuple", "group", "range", "not_entity",
    ],
)
def test_create_value_returns_converter_for_its_type(value: object, converter_type: type[AbstractConverter]):
    """Фабрика выбирает конвертер по типу значения, в том числе по базовому классу: bool — через int,
    datetime — через date, перечисление — через Enum, любая модель — через object."""
    # Действие
    converter = ConverterFactory().create(value)

    # Проверка
    assert type(converter) is converter_type


def test_create_same_type_returns_same_converter():
    """Конвертеры без состояния создаются один раз: для одного типа фабрика выдаёт тот же экземпляр."""
    # Подготовка
    factory = ConverterFactory()

    # Действие
    first = factory.create("Мука")
    second = factory.create(42)

    # Проверка
    assert first is second


# ---------------------------------------------------------------------------
# convert(): простые и составные модели
# ---------------------------------------------------------------------------


def test_convert_group_returns_dict_of_fields():
    """Модель с простыми полями превращается в словарь «наименование поля — значение», код — строкой."""
    # Подготовка
    group = NomenclatureGroupModel("Мясные продукты")

    # Действие
    result = ConverterFactory().convert(group)

    # Проверка
    assert result == {"id": str(group.id), "name": "Мясные продукты"}


def test_convert_base_range_returns_reference_instead_of_self():
    """Базовая единица ссылается сама на себя: вместо бесконечной рекурсии base записывается ссылкой по коду."""
    # Подготовка
    piece = RangeModel.create_piece()

    # Действие
    result = ConverterFactory().convert(piece)

    # Проверка
    assert result == _base_range_dict(piece)


def test_convert_derived_range_returns_nested_base():
    """Производная единица раскрывает базовую вложенным словарём, а та — снова ссылку на себя (словарь в словаре)."""
    # Подготовка
    kilogram = RangeModel.create_kilogram()

    # Действие
    result = ConverterFactory().convert(kilogram)

    # Проверка
    assert result == {
        "id": str(kilogram.id),
        "name": "килограмм",
        "base": _base_range_dict(kilogram.base),
        "factor": 1000,
        "is_base": False,
    }


def test_convert_nomenclature_returns_nested_references_in_field_order():
    """Номенклатура раскрывает группу и единицу вложенными словарями, тип записывается значением перечисления.
    Ключи идут в порядке объявления полей."""
    # Подготовка
    group = NomenclatureGroupModel("Бакалея")
    kilogram = RangeModel.create_kilogram()
    flour = NomenclatureModel.create_raw_material("Мука", "Мука пшеничная", group, kilogram, 1)

    # Действие
    result = ConverterFactory().convert(flour)

    # Проверка
    assert list(result) == ["id", "name", "full_name", "group", "range", "type", "grams_per_base_unit"]
    assert result["group"] == _group_dict(group)
    assert result["range"] == ConverterFactory().convert(kilogram)
    assert result["type"] == "сырьё"
    assert result["grams_per_base_unit"] == 1


def test_convert_recipe_returns_lists_of_steps_and_ingredients():
    """Карта записывает шаги списком строк, а состав — списком словарей ингредиентов с вложенной номенклатурой."""
    # Подготовка
    group = NomenclatureGroupModel("Бакалея")
    gram = RangeModel("грамм", 1)
    piece = RangeModel.create_piece()
    flour = _raw_material("Мука", group, gram)
    bread = NomenclatureModel.create_dish("Хлеб", "Хлеб пшеничный", group, piece, 500)
    recipe = RecipeModel("Хлеб", bread, 1, 60, ["Замесить", "Испечь"], [IngredientModel(flour, 400, 0.25)])

    # Действие
    result = ConverterFactory().convert(recipe)

    # Проверка
    assert result["result"] == ConverterFactory().convert(bread)
    assert result["steps"] == ["Замесить", "Испечь"]
    assert result["items"] == [
        {
            "nomenclature": ConverterFactory().convert(flour),
            "quantity": 400,
            "loss_ratio": 0.25,
            "base": [],
            "gross_weight": 400,
            "net_weight": 300,
        }
    ]


def test_convert_composite_ingredient_returns_nested_base():
    """Ингредиент-полуфабрикат раскрывает основание рекурсивно: в нём лежат словари ингредиентов его карты."""
    # Подготовка
    group = NomenclatureGroupModel("Полуфабрикаты")
    gram = RangeModel("грамм", 1)
    beef = _raw_material("Говядина", group, gram)
    bouillon = NomenclatureModel.create_semi_finished("Бульон", "Бульон говяжий", group, gram, 1)
    recipe = RecipeModel("Бульон", bouillon, 1000, 60, ["Варить"], [IngredientModel(beef, 500)])
    ingredient = recipe.as_ingredient(300)

    # Действие
    result = ConverterFactory().convert(ingredient)

    # Проверка
    assert result["nomenclature"] == ConverterFactory().convert(bouillon)
    assert result["quantity"] == 300
    base = result["base"]
    assert isinstance(base, list)
    assert len(base) == 1  # pyright: ignore[reportUnknownArgumentType]
    assert base[0] == ConverterFactory().convert(ingredient.base[0])
    assert base[0]["quantity"] == 150  # pyright: ignore[reportUnknownMemberType]


def test_convert_object_with_dates_returns_iso_strings():
    """Поле-дата и список дат записываются строками ISO 8601."""
    # Подготовка
    event = _Event("Инвентаризация", datetime(2026, 10, 22, 9, 0, tzinfo=UTC), [date(2026, 10, 23), date(2026, 10, 24)])

    # Действие
    result = ConverterFactory().convert(event)

    # Проверка
    assert result == {
        "title": "Инвентаризация",
        "created_at": "2026-10-22T09:00:00+00:00",
        "dates": ["2026-10-23", "2026-10-24"],
    }


def test_convert_shared_object_returns_full_dict_each_time():
    """Общий объект без цикла (одна группа в двух полях) раскрывается целиком в каждом поле, а не ссылкой."""
    # Подготовка
    group = NomenclatureGroupModel("Мясо")

    # Действие
    result = ConverterFactory().convert(_Pair(group, group))

    # Проверка
    assert result == {"first": _group_dict(group), "second": _group_dict(group)}


def test_convert_cycle_without_id_raises():
    """Объект без идентификатора, ссылающийся сам на себя, нельзя записать ссылкой."""
    # Подготовка
    pair = _Pair(None, None)
    pair._first = pair  # pyright: ignore[reportPrivateUsage]

    # Действие и проверка
    with pytest.raises(OperationException):
        _ = ConverterFactory().convert(pair)


def test_convert_after_error_returns_full_dict():
    """После ошибки фабрика очищает путь: следующий объект раскрывается целиком, а не ссылкой."""
    # Подготовка
    factory = ConverterFactory()
    group = NomenclatureGroupModel("Мясо")
    broken = _Pair(group, None)
    broken._second = broken  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(OperationException):
        _ = factory.convert(broken)

    # Действие
    result = factory.convert(_Pair(group, None))

    # Проверка
    assert result == {"first": _group_dict(group), "second": None}


# Подготовка
@pytest.mark.parametrize(
    "source",
    ["Мука", 1, None, NomenclatureType.DISH, date(2026, 10, 22), ["Мука"]],
    ids=["str", "int", "none", "enum", "date", "list"],
)
def test_convert_value_without_fields_raises(source: object):
    """Простое значение, дата и список не имеют полей: превратить их в словарь полей нельзя."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ConverterFactory().convert(source)


def test_convert_result_is_serialized_by_json_without_changes():
    """Результат записывается json.dumps без настроек и читается обратно тем же словарём."""
    # Подготовка
    group = NomenclatureGroupModel("Бакалея")
    flour = _raw_material("Мука", group, RangeModel.create_kilogram())
    result = ConverterFactory().convert(flour)

    # Действие
    restored: object = json.loads(json.dumps(result, ensure_ascii=False))

    # Проверка
    assert restored == result
