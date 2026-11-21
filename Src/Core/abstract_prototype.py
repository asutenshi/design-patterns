from abc import ABC, abstractmethod
from typing import cast

from Src.Core.common_validator import CommonValidator
from Src.Dtos.filter_dto import FilterDto


class AbstractPrototype[T](ABC):
    """Абстрактный прототип: набор данных, который умеет создавать свою копию с отобранными элементами.

    Исходный прототип при клонировании не меняется. Копируется только список, сами элементы остаются
    теми же объектами, поэтому коллекции хранилища не затрагиваются, а модели не дублируются.
    """

    # Данные прототипа
    _data: list[T]

    def __init__(self, data: list[T]) -> None:
        """Инициализирует прототип копией списка данных.

        :param data: Элементы прототипа.
        :raises ArgumentsException: Если передан не список.
        """
        items = cast(list[T], CommonValidator.validate_instance(data, list, "data", "Ожидается список данных"))
        self._data = list(items)

    @property
    def data(self) -> list[T]:
        """Возвращает копию списка данных прототипа."""
        return list(self._data)

    @abstractmethod
    def clone(self, filter_dto: FilterDto) -> "AbstractPrototype[T]":
        """Создаёт новый прототип из элементов, которые прошли все условия фильтра.

        :param filter_dto: Условия фильтрации.
        :return: Новый прототип с отобранными элементами.
        """
