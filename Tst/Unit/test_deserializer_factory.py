import uuid
from typing import Self, cast, override

import pytest
from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.abstract_model import AbstractModel
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
from Src.Logics.basic_deserializer import BasicDeserializer
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Logics.list_deserializer import ListDeserializer
from Src.Logics.model_deserializer import ModelDeserializer


class ItemStub(NamedEntity):
    """Простая модель-заглушка без вложенных моделей. Запоминает ключи, которые получила в from_dict."""

    received: set[str]

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Создаёт модель по наименованию."""
        item = cls(cast(str, data["name"]))
        item.received = set(data)
        return item


class ParentStub(NamedEntity):
    """Модель-заглушка с вложенной моделью и списком вложенных моделей."""

    child: ItemStub
    others: list[ItemStub]

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Создаёт модель, вложенные модели в данных уже собраны."""
        parent = cls(cast(str, data["name"]))
        parent.child = cast(ItemStub, data["child"])
        parent.others = cast(list[ItemStub], data["others"])
        return parent


class NodeStub(NamedEntity):
    """Модель-заглушка со ссылкой на другую модель того же типа: для проверки циклов."""

    link: "NodeStub | None"

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Создаёт узел, ссылка в данных уже собрана или None (цикл)."""
        node = cls(cast(str, data["name"]))
        node.link = cast(NodeStub | None, data["link"])
        return node


class LineStub(AbstractModel):
    """Модель-заглушка без идентификатора, как строка состава карты."""

    quantity: float

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Создаёт строку по количеству."""
        line = cls()
        line.quantity = cast(float, data["quantity"])
        return line


class BrokenStub(NamedEntity):
    """Модель-заглушка, чей from_dict всегда отклоняет данные."""

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Отклоняет данные."""
        raise ArgumentsException("name", "Модель-заглушка не собирается")


def _type(model_class: type) -> str:
    """Возвращает тип модели так, как его записывает ConverterFactory."""
    return f"{model_class.__module__}.{model_class.__qualname__}"


def _item(name: str = "Мука") -> dict[str, object]:
    """Создаёт данные простой модели с новым идентификатором."""
    return {"model_type": _type(ItemStub), "id": str(uuid.uuid4()), "name": name}


def _parent(child: object, others: list[object]) -> dict[str, object]:
    """Создаёт данные модели с вложенными моделями."""
    return {"model_type": _type(ParentStub), "id": str(uuid.uuid4()), "name": "Набор", "child": child, "others": others}


# ---------------------------------------------------------------------------
# create(): выбор десериализатора по виду значения
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize(
    ("value", "deserializer_type"),
    [
        ("Мука", BasicDeserializer),
        (1, BasicDeserializer),
        (1.5, BasicDeserializer),
        (True, BasicDeserializer),
        (None, BasicDeserializer),
        (["Мука"], ListDeserializer),
        ({"name": "Мука"}, ModelDeserializer),
    ],
    ids=["str", "int", "float", "bool", "none", "list", "dict"],
)
def test_create_json_value_returns_deserializer_for_its_kind(value: object, deserializer_type: type):
    """Фабрика выбирает десериализатор по виду значения, а не по модели: bool находится через int."""
    # Действие
    deserializer = DeserializerFactory().create(value)

    # Проверка
    assert type(deserializer) is deserializer_type


# Подготовка
@pytest.mark.parametrize("value", [("Мука",), {"Мука"}, object()], ids=["tuple", "set", "object"])
def test_create_not_json_value_raises(value: object):
    """Значение, которого не бывает в JSON, — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().create(value)


def test_create_same_kind_returns_same_deserializer():
    """Десериализаторы создаются один раз: для одного вида значений фабрика выдаёт тот же экземпляр."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие
    first = factory.create("Мука")
    second = factory.create(42)

    # Проверка
    assert isinstance(first, AbstractDeserializer)
    assert first is second


# ---------------------------------------------------------------------------
# deserialize(): простые значения, списки и модели
# ---------------------------------------------------------------------------


# Подготовка
@pytest.mark.parametrize(
    "value",
    ["Мука", 1, 1.5, True, None, [], ["Мука", 1, None, ["вложенный"]]],
    ids=["str", "int", "float", "bool", "none", "empty_list", "list"],
)
def test_deserialize_value_without_model_returns_same_data(value: object):
    """Простые значения и списки из них возвращаются как есть: перечисления и даты превращает уже модель."""
    # Действие
    result = DeserializerFactory().deserialize(value)

    # Проверка
    assert result == value


def test_deserialize_flat_model_returns_model_with_id_from_data():
    """Класс модели выбирается по model_type, идентификатор берётся из данных, а не генерируется."""
    # Подготовка
    data = _item("Сахар")

    # Действие
    result = DeserializerFactory().deserialize(data)

    # Проверка
    assert isinstance(result, ItemStub)
    assert result.name == "Сахар"
    assert str(result.id) == data["id"]


def test_deserialize_model_service_fields_not_passed_to_from_dict():
    """В from_dict не попадают id и model_type: модель получает только свои поля."""
    # Действие
    result = cast(ItemStub, DeserializerFactory().deserialize(_item()))

    # Проверка
    assert result.received == {"name"}


def test_deserialize_model_without_id_builds_model():
    """Модель без идентификатора (как строка состава) собирается и в кэш не попадает."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие
    with factory.session():
        result = factory.deserialize({"model_type": _type(LineStub), "quantity": 5})
        cache = dict(factory._cache)  # pyright: ignore[reportPrivateUsage]

    # Проверка
    assert isinstance(result, LineStub)
    assert result.quantity == 5
    assert cache == {}


def test_deserialize_nested_models_builds_them_recursively():
    """Вложенная модель и список вложенных моделей собираются рекурсивно, from_dict получает их готовыми."""
    # Подготовка
    data = _parent(_item("Соль"), [_item("Перец"), _item("Лавр")])

    # Действие
    result = DeserializerFactory().deserialize(data)

    # Проверка
    assert isinstance(result, ParentStub)
    assert isinstance(result.child, ItemStub)
    assert result.child.name == "Соль"
    assert [item.name for item in result.others] == ["Перец", "Лавр"]


def test_deserialize_list_of_models_returns_models_in_order():
    """Список моделей превращается в список моделей в исходном порядке."""
    # Действие
    result = DeserializerFactory().deserialize([_item("Соль"), _item("Перец")])

    # Проверка
    assert isinstance(result, list)
    assert [cast(ItemStub, item).name for item in cast(list[object], result)] == ["Соль", "Перец"]


def test_deserialize_repeated_id_returns_same_object():
    """Одна модель, встреченная полным словарём и ссылкой, собирается один раз: это один и тот же объект."""
    # Подготовка
    shared = _item("Соль")
    data = _parent(shared, [dict(shared), {"id": shared["id"]}])

    # Действие
    result = cast(ParentStub, DeserializerFactory().deserialize(data))

    # Проверка
    assert result.others[0] is result.child
    assert result.others[1] is result.child


def test_deserialize_reference_to_model_in_progress_returns_none():
    """Ссылка на модель, которая сейчас собирается (цикл), передаётся в from_dict как None."""
    # Подготовка
    node_id = str(uuid.uuid4())
    data = {"model_type": _type(NodeStub), "id": node_id, "name": "Узел", "link": {"id": node_id}}

    # Действие
    result = DeserializerFactory().deserialize(data)

    # Проверка
    assert isinstance(result, NodeStub)
    assert result.link is None


def test_deserialize_reference_to_built_model_returns_it():
    """Ссылка на модель, собранную раньше в тех же данных, — тот же объект, а не цикл."""
    # Подготовка
    first = {"model_type": _type(NodeStub), "id": str(uuid.uuid4()), "name": "Первый", "link": None}
    second = {"model_type": _type(NodeStub), "id": str(uuid.uuid4()), "name": "Второй", "link": {"id": first["id"]}}

    # Действие
    result = cast(list[NodeStub], DeserializerFactory().deserialize([first, second]))

    # Проверка
    assert result[1].link is result[0]


def test_deserialize_twice_does_not_share_objects():
    """Кэш живёт только одну загрузку: повторная загрузка тех же данных создаёт новые объекты."""
    # Подготовка
    factory = DeserializerFactory()
    data = _item()

    # Действие
    first = factory.deserialize(data)
    second = factory.deserialize(data)

    # Проверка
    assert first is not second
    assert first == second


# ---------------------------------------------------------------------------
# deserialize(): некорректные данные
# ---------------------------------------------------------------------------


def test_deserialize_reference_to_unknown_model_raises_and_clears_state():
    """Ссылка на модель, которой нет в данных, — OperationException; кэш и стек собираемых после ошибки пусты."""
    # Подготовка
    factory = DeserializerFactory()
    data = _parent(_item("Соль"), [{"id": str(uuid.uuid4())}])

    # Действие и проверка
    with pytest.raises(OperationException):
        factory.deserialize(data)
    # Соль к этому моменту уже была собрана и лежала в кэше, после ошибки её не должно остаться
    assert factory._cache == {}  # pyright: ignore[reportPrivateUsage]
    assert factory._in_progress == set()  # pyright: ignore[reportPrivateUsage]


def test_deserialize_dict_without_model_type_raises():
    """Словарь без model_type и не ссылка — ArgumentsException: неизвестно, какую модель собирать."""
    # Подготовка
    data = _item()
    del data["model_type"]

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(data)
    assert "model_type" in str(exc_info.value)


# Подготовка
@pytest.mark.parametrize(
    "model_type",
    ["Src.Models.missing_model.MissingModel", "os.system", _type(NamedEntity), _type(AbstractModel), 1, None],
    ids=["unknown", "not_model", "abstract_entity", "abstract_root", "int", "none"],
)
def test_deserialize_unknown_or_abstract_model_type_raises(model_type: object):
    """Неизвестный, абстрактный или нестроковый тип модели — ArgumentsException."""
    # Подготовка
    data = _item()
    data["model_type"] = model_type

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(data)


# Подготовка
@pytest.mark.parametrize("model_id", [1, None, "not-a-uuid"], ids=["int", "none", "not_uuid"])
def test_deserialize_invalid_id_raises(model_id: object):
    """Идентификатор не строка с UUID — ArgumentsException."""
    # Подготовка
    data = _item()
    data["id"] = model_id

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(data)


def test_deserialize_id_for_model_without_identity_raises():
    """Идентификатор у модели, которая не сущность (строка состава), — ArgumentsException."""
    # Подготовка
    data = {"model_type": _type(LineStub), "id": str(uuid.uuid4()), "quantity": 5}

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(data)


def test_deserialize_model_rejected_by_from_dict_raises_and_clears_state():
    """Ошибка from_dict доходит до клиента, а стек собираемых моделей после неё пуст."""
    # Подготовка
    factory = DeserializerFactory()
    data = {"model_type": _type(BrokenStub), "id": str(uuid.uuid4()), "name": "Сломанная"}

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        factory.deserialize(data)
    assert factory._in_progress == set()  # pyright: ignore[reportPrivateUsage]


def test_deserialize_dict_with_not_string_key_raises():
    """У JSON-объекта ключи — строки: словарь с числовым ключом — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize({1: "Мука"})


# ---------------------------------------------------------------------------
# deserialize_as(): проверка типа результата
# ---------------------------------------------------------------------------


def test_deserialize_as_expected_type_returns_model():
    """Данные с моделью ожидаемого типа возвращают эту модель."""
    # Действие
    result = DeserializerFactory().deserialize_as(ItemStub, _item("Соль"))

    # Проверка
    assert result.name == "Соль"


def test_deserialize_as_other_type_raises():
    """Тип не выбирает модель, а проверяет её: данные с другой моделью — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize_as(ParentStub, _item())


# Подготовка
@pytest.mark.parametrize("target_type", [None, "ItemStub", 1], ids=["none", "str", "int"])
def test_deserialize_as_not_a_type_raises(target_type: object):
    """Вместо типа передано другое значение — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize_as(target_type, _item())  # pyright: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# session(): общий кэш для нескольких вызовов
# ---------------------------------------------------------------------------


def test_session_deserialize_calls_share_objects():
    """В одной сессии модель, встреченная в разных вызовах, — один объект, а не копии."""
    # Подготовка
    factory = DeserializerFactory()
    shared = _item("Соль")

    # Действие
    with factory.session():
        first = factory.deserialize(shared)
        second = factory.deserialize({"id": shared["id"]})

    # Проверка
    assert second is first


def test_session_exit_clears_cache():
    """Выход из сессии очищает кэш, следующая загрузка начинается с чистого."""
    # Подготовка
    factory = DeserializerFactory()
    data = _item()

    # Действие
    with factory.session():
        inside = factory.deserialize(data)
    outside = factory.deserialize(data)

    # Проверка
    assert factory._cache == {}  # pyright: ignore[reportPrivateUsage]
    assert outside is not inside


def test_session_inside_cache_is_kept_between_calls():
    """Внутри сессии кэш между вызовами не сбрасывается, это и отличает её от обычного deserialize."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие и проверка
    with factory.session():
        _ = factory.deserialize(_item())
        assert len(factory._cache) == 1  # pyright: ignore[reportPrivateUsage]


def test_session_error_inside_clears_cache_and_allows_new_session():
    """Ошибка внутри сессии не оставляет в фабрике ни кэша, ни открытой сессии."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие
    with pytest.raises(OperationException), factory.session():
        _ = factory.deserialize(_item())
        _ = factory.deserialize({"id": str(uuid.uuid4())})

    # Проверка
    assert factory._cache == {}  # pyright: ignore[reportPrivateUsage]
    with factory.session():
        pass


def test_session_nested_raises():
    """Вложенная сессия — OperationException: она очистила бы кэш внешней раньше времени."""
    # Подготовка
    factory = DeserializerFactory()

    # Действие и проверка
    with factory.session(), pytest.raises(OperationException), factory.session():
        pass
