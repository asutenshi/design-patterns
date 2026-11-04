import uuid
from typing import ClassVar, override

import pytest
from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.warehouse_model import WarehouseModel


class ItemStub(NamedEntity):
    """Простая модель-заглушка без вложенных моделей."""


class ParentStub(NamedEntity):
    """Модель-заглушка с вложенной моделью и списком вложенных моделей."""

    def __init__(self, name: str, child: ItemStub, others: list[ItemStub]) -> None:
        """Сохраняет вложенные модели."""
        super().__init__(name)
        self.child = child
        self.others = others


class UnknownStub(NamedEntity):
    """Модель-заглушка, для которой десериализатора нет."""


class ItemDeserializerStub(AbstractDeserializer):
    """Десериализатор простой модели."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт модель по наименованию."""
        return ItemStub(str(data["name"]))


class ParentDeserializerStub(AbstractDeserializer):
    """Десериализатор модели с вложенными моделями: рекурсия идёт через resolve."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт модель, вложенные собирает через resolve."""
        child = self._resolve(ItemStub, data["child"])
        others = [self._resolve(ItemStub, item) for item in data["others"]]  # pyright: ignore[reportGeneralTypeIssues]
        return ParentStub(str(data["name"]), child, others)  # pyright: ignore[reportArgumentType]


class WrongDeserializerStub(AbstractDeserializer):
    """Неисправный десериализатор: для UnknownStub возвращает другую модель."""

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Возвращает модель не того типа."""
        return ItemStub(str(data["name"]))


class FactoryStub(DeserializerFactory):
    """Фабрика с заглушками вместо десериализаторов реальных моделей."""

    _deserializers: ClassVar[dict[type, type[AbstractDeserializer]]] = {
        ItemStub: ItemDeserializerStub,
        ParentStub: ParentDeserializerStub,
        UnknownStub: WrongDeserializerStub,
    }


def _item(name: str = "Мука") -> dict[str, object]:
    """Создаёт данные простой модели с новым идентификатором."""
    return {"id": str(uuid.uuid4()), "name": name}


def test_create_known_type_returns_its_deserializer():
    """Для зарегистрированного типа создаётся десериализатор нужного класса."""
    # Подготовка
    factory = FactoryStub()

    # Действие
    deserializer = factory.create(ItemStub)

    # Проверка
    assert isinstance(deserializer, ItemDeserializerStub)


def test_create_unregistered_type_raises():
    """Для типа без десериализатора выбрасывается ArgumentsException."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory.create(ItemStub)


# Подготовка
@pytest.mark.parametrize("target_type", [None, "ItemStub", 1, ItemStub("Мука")])
def test_create_not_a_type_raises(target_type):
    """Вместо типа передано другое значение: выбрасывается ArgumentsException."""
    # Подготовка
    factory = FactoryStub()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory.create(target_type)


def test_deserialize_flat_model_returns_model_with_id():
    """Простая модель собирается из данных, идентификатор берётся из данных, а не генерируется."""
    # Подготовка
    factory = FactoryStub()
    data = _item("Сахар")

    # Действие
    result = factory.deserialize(ItemStub, data)

    # Проверка
    assert isinstance(result, ItemStub)
    assert result.name == "Сахар"
    assert str(result.id) == data["id"]


def test_deserialize_nested_models_builds_them_recursively():
    """Вложенная модель и список вложенных моделей собираются рекурсивно."""
    # Подготовка
    factory = FactoryStub()
    data = {"id": str(uuid.uuid4()), "name": "Набор", "child": _item("Соль"), "others": [_item("Перец"), _item("Лавр")]}

    # Действие
    result = factory.deserialize(ParentStub, data)

    # Проверка
    assert result.child.name == "Соль"
    assert [item.name for item in result.others] == ["Перец", "Лавр"]


def test_deserialize_repeated_id_returns_same_object():
    """Одна модель, встреченная полным словарём и ссылкой, собирается один раз: это один и тот же объект."""
    # Подготовка
    factory = FactoryStub()
    shared = _item("Соль")
    data = {
        "id": str(uuid.uuid4()),
        "name": "Набор",
        "child": shared,
        "others": [dict(shared), {"id": shared["id"]}],
    }

    # Действие
    result = factory.deserialize(ParentStub, data)

    # Проверка
    assert result.others[0] is result.child
    assert result.others[1] is result.child


def test_deserialize_twice_does_not_share_objects():
    """Кэш живёт только одну загрузку: повторная загрузка тех же данных создаёт новые объекты."""
    # Подготовка
    factory = FactoryStub()
    data = _item()

    # Действие
    first = factory.deserialize(ItemStub, data)
    second = factory.deserialize(ItemStub, data)

    # Проверка
    assert first is not second
    assert first == second


def test_deserialize_reference_to_unknown_model_raises_and_clears_cache():
    """Ссылка на модель, которой нет в данных, — OperationException; кэш после ошибки очищается."""
    # Подготовка
    factory = FactoryStub()
    known = _item("Соль")
    data = {"id": str(uuid.uuid4()), "name": "Набор", "child": known, "others": [{"id": str(uuid.uuid4())}]}

    # Действие и проверка
    with pytest.raises(OperationException):
        factory.deserialize(ParentStub, data)
    # Соль к этому моменту уже была собрана и лежала в кэше, после ошибки его не должно остаться
    assert factory._cache == {}


def test_deserialize_wrong_result_type_raises():
    """Десериализатор вернул модель другого типа, чем запрошена, — ArgumentsException."""
    # Подготовка
    factory = FactoryStub()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory.deserialize(UnknownStub, {"name": "Соль"})


def test_deserialize_not_a_dict_raises():
    """Данные не словарь: выбрасывается ArgumentsException."""
    # Подготовка
    factory = FactoryStub()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory.deserialize(ItemStub, ["Мука"])


# Подготовка
@pytest.mark.parametrize(
    "target_type",
    [RangeModel, NomenclatureGroupModel, NomenclatureModel, WarehouseModel, IngredientModel, RecipeModel],
)
def test_create_real_factory_model_has_deserializer(target_type: type):
    """Для каждой модели из домена в рабочей фабрике зарегистрирован десериализатор."""
    # Действие
    deserializer = DeserializerFactory().create(target_type)

    # Проверка
    assert isinstance(deserializer, AbstractDeserializer)


def test_session_deserialize_calls_share_objects():
    """В одной сессии модель, встреченная в разных вызовах, — один объект, а не копии."""
    # Подготовка
    factory = FactoryStub()
    shared = _item("Соль")

    # Действие
    with factory.session():
        first = factory.deserialize(ItemStub, shared)
        second = factory.deserialize(ItemStub, {"id": shared["id"]})

    # Проверка
    assert second is first


def test_session_exit_clears_cache():
    """Выход из сессии очищает кэш, следующая загрузка начинается с чистого."""
    # Подготовка
    factory = FactoryStub()
    data = _item()

    # Действие
    with factory.session():
        inside = factory.deserialize(ItemStub, data)
    outside = factory.deserialize(ItemStub, data)

    # Проверка
    assert factory._cache == {}
    assert outside is not inside


def test_session_inside_cache_is_kept_between_calls():
    """Внутри сессии кэш между вызовами не сбрасывается, это и отличает её от обычного deserialize."""
    # Подготовка
    factory = FactoryStub()

    # Действие и проверка
    with factory.session():
        _ = factory.deserialize(ItemStub, _item())
        assert len(factory._cache) == 1


def test_session_error_inside_clears_cache_and_allows_new_session():
    """Ошибка внутри сессии не оставляет в фабрике ни кэша, ни открытой сессии."""
    # Подготовка
    factory = FactoryStub()

    # Действие
    with pytest.raises(OperationException), factory.session():
        _ = factory.deserialize(ItemStub, _item())
        _ = factory.deserialize(ItemStub, {"id": str(uuid.uuid4())})

    # Проверка
    assert factory._cache == {}
    with factory.session():
        pass


def test_session_nested_raises():
    """Вложенная сессия — OperationException: она очистила бы кэш внешней раньше времени."""
    # Подготовка
    factory = FactoryStub()

    # Действие и проверка
    with factory.session(), pytest.raises(OperationException), factory.session():
        pass
