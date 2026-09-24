import uuid

import pytest

from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException


class EntityStub(BaseEntity):
    """Минимальная конкретная сущность для проверки поведения BaseEntity."""


def test_id_getter_new_entity_not_none():
    """У только что созданной сущности идентификатор задан."""
    # Подготовка
    entity = EntityStub('a')

    # Действие
    result = entity.id

    # Проверка
    assert result is not None


def test_id_getter_two_entities_different_ids():
    """Две разные сущности получают разные идентификаторы."""
    # Подготовка
    entity1 = EntityStub('a')
    entity2 = EntityStub('b')

    # Действие
    id1 = entity1.id
    id2 = entity2.id

    # Проверка
    assert id1 != id2


def test_eq_same_id_entities_equal():
    """Сущности одного типа с одинаковым идентификатором считаются равными."""
    # Подготовка
    entity1 = EntityStub('a')
    entity2 = EntityStub('b')
    new_id = uuid.uuid4()

    # Действие
    entity1.id = new_id
    entity2.id = new_id

    # Проверка
    assert entity1 == entity2


def test_init_empty_name_raises():
    """Создание сущности с пустым наименованием вызывает ArgumentsException."""
    # Подготовка
    name = ''

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        EntityStub(name)


def test_init_none_name_raises():
    """Создание сущности с наименованием None вызывает ArgumentsException."""
    # Подготовка
    name = None

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        EntityStub(name)  # pyright: ignore[reportArgumentType]
