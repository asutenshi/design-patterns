import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Core.named_entity import NamedEntity


class NamedEntityStub(NamedEntity):
    """Минимальная конкретная сущность для проверки поведения NamedEntity."""


def test_name_getter_valid_name_returned():
    """Геттер возвращает наименование, переданное при создании."""
    # Подготовка
    entity = NamedEntityStub("Мука")

    # Действие
    result = entity.name

    # Проверка
    assert result == "Мука"


def test_name_getter_surrounding_spaces_stripped():
    """Пробелы по краям наименования обрезаются."""
    # Подготовка
    entity = NamedEntityStub("  Мука  ")

    # Действие
    result = entity.name

    # Проверка
    assert result == "Мука"


def test_name_setter_valid_name_replaces_old():
    """Сеттер меняет наименование уже созданной сущности."""
    # Подготовка
    entity = NamedEntityStub("Мука")

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
        NamedEntityStub(name)


# Подготовка
@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_name_setter_invalid_name_raises(name):
    """Сеттер отклоняет пустое, состоящее из пробелов или не строковое наименование."""
    # Подготовка
    entity = NamedEntityStub("Мука")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        entity.name = name


def test_name_setter_invalid_name_old_value_kept():
    """После отклонённого наименования сохраняется прежнее."""
    # Подготовка
    entity = NamedEntityStub("Мука")

    # Действие
    with pytest.raises(ArgumentsException):
        entity.name = ""

    # Проверка
    assert entity.name == "Мука"



def test_init_any_instance_is_base_entity():
    """Сущность с наименованием является наследником BaseEntity и получает идентификатор."""
    # Подготовка
    entity = NamedEntityStub("Мука")

    # Действие
    result = isinstance(entity, BaseEntity)

    # Проверка
    assert result is True


def test_hash_after_rename_unchanged():
    """Хэш определяется идентификатором и не меняется при переименовании."""
    # Подготовка
    entity = NamedEntityStub("a")
    old_hash = hash(entity)

    # Действие
    entity.name = "b"

    # Проверка
    assert hash(entity) == old_hash
