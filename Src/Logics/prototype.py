from enum import Enum
from typing import assert_never, cast, override

from Src.Core.abstract_prototype import AbstractPrototype
from Src.Core.filter_type import FilterType
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.filter_item_dto import FilterItemDto
from Src.Logics.field_path_reader import FieldPathReader


class Prototype[T](AbstractPrototype[T]):
    """Прототип доменных моделей любого типа: фильтрует их по условиям из ``FilterDto``.

    Значения полей читает ``FieldPathReader``, поэтому новая модель работает без правок прототипа.
    Модель проходит условие, если совпало хотя бы одно значение, найденное по пути.
    Значения сравниваются строками: ``EQUALS`` — полное совпадение, ``LIKE`` — вхождение, регистр учитывается.
    """

    # Читает значения полей модели по пути
    _reader: FieldPathReader

    def __init__(self, data: list[T]) -> None:
        """Инициализирует прототип.

        :param data: Модели прототипа.
        :raises ArgumentsException: Если передан не список.
        """
        super().__init__(data)
        self._reader = FieldPathReader()

    @override
    def clone(self, filter_dto: FilterDto) -> "Prototype[T]":
        """Создаёт новый прототип из моделей, которые прошли все условия фильтра.

        :param filter_dto: Условия фильтрации. Пустой набор условий пропускает все модели.
        :return: Новый прототип, даже если условий нет.
        :raises ArgumentsException: Если путь условия ведёт к недоступному полю.
        """
        filters = filter_dto.filters

        if filters:
            filtered = [item for item in self.data if self._matches(item, filters[0])]
            return Prototype(filtered).clone(FilterDto(filters[1:]))

        return Prototype(self.data)

    def _matches(self, model: T, item: FilterItemDto) -> bool:
        """Проверяет, проходит ли модель одно условие фильтра.

        :param model: Проверяемая модель.
        :param item: Условие фильтрации.
        :return: True, если хотя бы одно значение по пути совпало с условием.
        :raises ArgumentsException: Если путь условия ведёт к недоступному полю.
        """
        values = [self._to_text(value) for value in self._reader.read(model, item.field_name)]

        match item.filter_type:
            case FilterType.EQUALS:
                return any(item.value == value for value in values)
            case FilterType.LIKE:
                return any(item.value in value for value in values)
            case _:
                # Новое значение FilterType без своей ветки — ошибка проверки типов, а не тихий False
                assert_never(item.filter_type)

    @staticmethod
    def _to_text(value: object) -> str:
        """Превращает значение поля в строку для сравнения с условием.

        У перечисления сравнивается значение (``"сырьё"``), а не имя (``NomenclatureType.RAW_MATERIAL``):
        так же оно записано в выгрузке и в теле запроса API.

        :param value: Значение поля модели.
        :return: Строковое представление значения.
        """
        if isinstance(value, Enum):
            return str(cast(object, value.value))
        return str(value)
