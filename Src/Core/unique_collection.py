from collections.abc import Callable, Hashable, Iterator

from Src.Core.exception import ArgumentsException


class UniqueCollection[T]:
    """Коллекция без дубликатов: два элемента с одинаковым ключом не допускаются.

    Ключ вычисляет переданная функция, например по наименованию. Порядок добавления сохраняется.
    Класс не привязан к доменным моделям, поэтому подходит и для будущих сущностей
    (ключом может быть и составное значение, например пара «помещение, наименование»).
    """

    # Функция, по которой определяется уникальность элемента
    _key: Callable[[T], Hashable]
    # Элементы по их ключам в порядке добавления
    _items: dict[Hashable, T]

    def __init__(self, key: Callable[[T], Hashable]) -> None:
        """Инициализирует пустую коллекцию.

        :param key: Функция, возвращающая хэшируемый ключ уникальности элемента.
        """
        self._key = key
        self._items = {}

    def add(self, item: T) -> None:
        """Добавляет элемент в коллекцию.

        :param item: Добавляемый элемент.
        :raises ArgumentsException: Если элемент с таким ключом уже есть в коллекции.
        """
        item_key = self._key(item)
        if item_key in self._items:
            raise ArgumentsException("item", f"Элемент с ключом {item_key!r} уже есть в коллекции")

        self._items[item_key] = item

    def remove(self, key: Hashable) -> None:
        """Удаляет из коллекции элемент по его ключу.

        Принимает именно ключ, а не элемент: вызывающему коду часто известен только ключ
        (например, идентификатор номенклатуры), а самого элемента у него нет.

        :param key: Ключ удаляемого элемента, то есть то, что возвращает функция ключа коллекции.
        :raises ArgumentsException: Если элемента с таким ключом нет в коллекции.
        """
        if key not in self._items:
            raise ArgumentsException("key", f"Элемента с ключом {key!r} нет в коллекции")

        del self._items[key]

    def key_of(self, item: T) -> Hashable:
        """Возвращает ключ уникальности элемента по функции ключа коллекции.

        Нужен, когда ключ элемента изменился после добавления (например, переименовали): коллекция хранит
        элемент под ключом, вычисленным при добавлении, и менять его надо через ``remove`` и ``add``.

        :param item: Элемент, не обязательно находящийся в коллекции.
        :return: Ключ элемента.
        """
        return self._key(item)

    def has_key(self, key: Hashable) -> bool:
        """Проверяет, есть ли в коллекции элемент с таким ключом.

        :param key: Ключ, то есть то, что возвращает функция ключа коллекции.
        :return: True, если элемент с таким ключом есть.
        """
        return key in self._items

    def __iter__(self) -> Iterator[T]:
        """Возвращает итератор по элементам в порядке добавления."""
        return iter(self._items.values())

    def __len__(self) -> int:
        """Возвращает количество элементов."""
        return len(self._items)