from enum import Enum
from typing import Protocol, Self, cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Core.sort_order import SortOrder
from Src.Dtos.sort_dto import SortDto
from Src.Logics.field_path_reader import FieldPathReader


class _Sortable(Protocol):
    """Протокол значения, поддерживающего сравнение на меньше."""

    def __lt__(self, other: Self, /) -> bool:
        """Возвращает True, если текущее значение меньше другого."""
        ...


class Sorter:
    """Универсальный сортировщик коллекций доменных моделей по пути к публичному полю.

    Значение поля читается через ``FieldPathReader``, поэтому новая модель работает без правок
    сортировщика. Исходный список не изменяется — возвращается новый отсортированный список.
    """

    # Читает значения полей модели по пути
    _reader: FieldPathReader

    def __init__(self, reader: FieldPathReader | None = None) -> None:
        """Инициализирует сортировщик.

        :param reader: Объект чтения полей по пути; ``None`` — новый ``FieldPathReader``.
        :raises ArgumentsException: Если передан не ``FieldPathReader``.
        """
        self._reader = (
            FieldPathReader()
            if reader is None
            else CommonValidator.validate_instance(reader, FieldPathReader, "reader", "Ожидается FieldPathReader")
        )

    def sort[T](self, items: list[T], sort_dto: SortDto) -> list[T]:
        """Возвращает новый список моделей, отсортированный по условию ``sort_dto``.

        :param items: Исходный список моделей.
        :param sort_dto: Путь к полю и направление сортировки.
        :return: Новый отсортированный список.
        :raises ArgumentsException: Если аргументы неверного типа, поле недоступно, путь ведёт
            к коллекции с неоднозначным числом значений или значения поля нельзя сравнить.
        """
        validated_items = cast(list[T], CommonValidator.validate_instance(items, list, "items", "Ожидается список"))
        sort_dto = CommonValidator.validate_instance(sort_dto, SortDto, "sort_dto", "Ожидаются параметры сортировки")
        reverse = sort_dto.direction == SortOrder.DESC
        try:
            return sorted(validated_items, key=lambda x: self._extract_key(x, sort_dto.field_name), reverse=reverse)
        except TypeError as e:
            raise ArgumentsException("field_name", f"Значения поля {sort_dto.field_name} нельзя сравнить: {e}") from e

    def _extract_key(self, item: object, field_name: str) -> _Sortable:
        """Извлекает сравнимое значение поля модели по пути.

        Перечисление приводится к ``value``, потому что ``Enum`` в Python не поддерживает операции
        сравнения. Путь через коллекцию с нулём или несколькими значениями отклоняется.

        :param item: Модель из сортируемого списка.
        :param field_name: Путь к публичному полю.
        :return: Значение ключа сортировки.
        :raises ArgumentsException: Если поле недоступно или по пути найдено не ровно одно значение.
        """
        values = self._reader.read(item, field_name)
        if len(values) != 1:
            raise ArgumentsException("field_name", f"Поле {field_name} должно давать ровно одно значение")
        single = values[0]
        raw_key: object = cast(object, single.value) if isinstance(single, Enum) else single
        return cast(_Sortable, raw_key)