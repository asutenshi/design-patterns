import uuid

import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException


class EntityStub(BaseEntity):
    """Минимальная конкретная сущность для проверки поведения BaseEntity."""


class OtherEntityStub(BaseEntity):
    """Вторая конкретная сущность другого типа для проверки сравнения по типу."""


def test_id_getter_new_entity_not_none():
    """У только что созданной сущности идентификатор задан."""
    # Подготовка
    entity = EntityStub("a")

    # Действие
    result = entity.id

    # Проверка
    assert result is not None


def test_id_getter_new_entity_is_uuid():
    """Идентификатор новой сущности имеет тип uuid.UUID."""
    # Подготовка
    entity = EntityStub("a")

    # Действие
    result = entity.id

    # Проверка
    assert isinstance(result, uuid.UUID)


def test_id_getter_two_entities_different_ids():
    """Две разные сущности получают разные идентификаторы."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("b")

    # Действие
    id1 = entity1.id
    id2 = entity2.id

    # Проверка
    assert id1 != id2


def test_id_setter_uuid_stored():
    """Сеттер идентификатора принимает uuid.UUID и сохраняет именно это значение."""
    # Подготовка
    entity = EntityStub("a")
    new_id = uuid.uuid4()

    # Действие
    entity.id = new_id

    # Проверка
    assert entity.id == new_id


# Подготовка
@pytest.mark.parametrize("value", ["", "not-a-uuid", str(uuid.uuid4()), None, 123, uuid.uuid4().int])
def test_id_setter_not_uuid_raises(value):
    """Значение, не являющееся uuid.UUID (в том числе строка или число с видом UUID), вызывает ArgumentsException."""
    # Подготовка
    entity = EntityStub("a")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        entity.id = value


def test_id_setter_not_uuid_id_unchanged():
    """После отклонённого значения идентификатор остаётся прежним."""
    # Подготовка
    entity = EntityStub("a")
    old_id = entity.id

    # Действие
    with pytest.raises(ArgumentsException):
        entity.id = "not-a-uuid"  # pyright: ignore[reportAttributeAccessIssue]

    # Проверка
    assert entity.id == old_id


def test_name_getter_valid_name_returned():
    """Геттер возвращает наименование, переданное при создании."""
    # Подготовка
    entity = EntityStub("Мука")

    # Действие
    result = entity.name

    # Проверка
    assert result == "Мука"


def test_name_getter_surrounding_spaces_stripped():
    """Пробелы по краям наименования обрезаются."""
    # Подготовка
    entity = EntityStub("  Мука  ")

    # Действие
    result = entity.name

    # Проверка
    assert result == "Мука"


def test_name_setter_valid_name_replaces_old():
    """Сеттер меняет наименование уже созданной сущности."""
    # Подготовка
    entity = EntityStub("Мука")

    # Действие
    entity.name = "Сахар"

    # Проверка
    assert entity.name == "Сахар"


# Подготовка
@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_init_invalid_name_raises(name):
    """Пустое, состоящее из пробелов или не строковое наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        EntityStub(name)


# Подготовка
@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_name_setter_invalid_name_raises(name):
    """Сеттер отклоняет пустое, состоящее из пробелов или не строковое наименование."""
    # Подготовка
    entity = EntityStub("Мука")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        entity.name = name


def test_name_setter_invalid_name_old_value_kept():
    """После отклонённого наименования сохраняется прежнее."""
    # Подготовка
    entity = EntityStub("Мука")

    # Действие
    with pytest.raises(ArgumentsException):
        entity.name = ""

    # Проверка
    assert entity.name == "Мука"


def test_eq_same_id_entities_equal():
    """Сущности одного типа с одинаковым идентификатором считаются равными."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("b")
    new_id = uuid.uuid4()

    # Действие
    entity1.id = new_id
    entity2.id = new_id

    # Проверка
    assert entity1 == entity2


def test_eq_different_id_entities_not_equal():
    """Сущности одного типа с разными идентификаторами не равны, даже при одинаковом наименовании."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("a")

    # Действие
    result = entity1 == entity2

    # Проверка
    assert result is False


def test_eq_same_id_different_types_not_equal():
    """Сущности разных типов с одинаковым идентификатором не равны."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = OtherEntityStub("a")
    entity2.id = entity1.id

    # Действие
    result = entity1 == entity2

    # Проверка
    assert result is False


# Подготовка
@pytest.mark.parametrize("other", [None, "a", 1, object()])
def test_eq_not_entity_returns_false(other):
    """Сравнение с объектом, не являющимся сущностью, даёт False без исключения."""
    # Подготовка
    entity = EntityStub("a")

    # Действие
    result = entity == other

    # Проверка
    assert result is False


def test_hash_equal_entities_equal_hashes():
    """Равные сущности имеют одинаковый хэш."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("b")
    entity2.id = entity1.id

    # Действие
    hash1 = hash(entity1)
    hash2 = hash(entity2)

    # Проверка
    assert hash1 == hash2


def test_hash_entities_with_same_id_single_set_element():
    """В множестве равные сущности занимают один элемент, разные — отдельные."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("b")
    entity2.id = entity1.id
    entity3 = EntityStub("c")

    # Действие
    result = {entity1, entity2, entity3}

    # Проверка
    assert len(result) == 2


def test_hash_entity_as_dict_key_found_by_equal_entity():
    """Сущность работает ключом словаря: значение находится по равной сущности."""
    # Подготовка
    entity1 = EntityStub("a")
    entity2 = EntityStub("b")
    entity2.id = entity1.id
    storage = {entity1: "value"}

    # Действие
    result = storage[entity2]

    # Проверка
    assert result == "value"


def test_hash_after_rename_unchanged():
    """Хэш определяется идентификатором и не меняется при переименовании."""
    # Подготовка
    entity = EntityStub("a")
    old_hash = hash(entity)

    # Действие
    entity.name = "b"

    # Проверка
    assert hash(entity) == old_hash
