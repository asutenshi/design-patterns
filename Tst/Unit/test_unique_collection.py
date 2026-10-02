import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.unique_collection import UniqueCollection


def test_init_new_collection_is_empty():
    """Новая коллекция не содержит элементов."""
    # Действие
    collection = UniqueCollection[str](lambda item: item)

    # Проверка
    assert len(collection) == 0
    assert list(collection) == []


def test_add_different_keys_are_stored_in_insertion_order():
    """Элементы с разными ключами сохраняются в порядке добавления."""
    # Подготовка
    collection = UniqueCollection[str](lambda item: item)

    # Действие
    collection.add("b")
    collection.add("a")
    collection.add("c")

    # Проверка
    assert list(collection) == ["b", "a", "c"]
    assert len(collection) == 3


def test_add_duplicate_key_raises_and_collection_is_unchanged():
    """Элемент с уже занятым ключом отклоняется, коллекция не меняется."""
    # Подготовка
    collection = UniqueCollection[str](lambda item: item)
    collection.add("a")

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        collection.add("a")
    assert "item" in str(exc_info.value)
    assert list(collection) == ["a"]


def test_add_same_key_different_items_raises():
    """Уникальность определяется ключом, а не самим элементом."""
    # Подготовка
    collection = UniqueCollection[tuple[str, int]](lambda item: item[0])
    collection.add(("a", 1))

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        collection.add(("a", 2))


def test_add_composite_key_allows_same_part_with_different_other_part():
    """Составной ключ допускает совпадение одной из частей."""
    # Подготовка
    collection = UniqueCollection[tuple[str, int]](lambda item: item)

    # Действие
    collection.add(("a", 1))
    collection.add(("a", 2))

    # Проверка
    assert len(collection) == 2


def test_iter_changing_collection_does_not_affect_other_collection():
    """Две коллекции независимы: ключи одной не занимают ключи другой."""
    # Подготовка
    first = UniqueCollection[str](lambda item: item)
    second = UniqueCollection[str](lambda item: item)

    # Действие
    first.add("a")
    second.add("a")

    # Проверка
    assert list(first) == ["a"]
    assert list(second) == ["a"]