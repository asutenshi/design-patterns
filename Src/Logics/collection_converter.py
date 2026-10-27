from collections.abc import Callable, Sequence
from typing import cast, override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException


class CollectionConverter(AbstractConverter):
    """Конвертер списков: список или кортеж записывается списком данных элементов.

    Каждый элемент превращается в данные функцией конвертации — обычно это ``ConverterFactory.convert``.
    Поэтому в одном списке могут лежать и строки, и модели, и вложенные списки.
    """

    # Функция, превращающая элемент в данные для JSON
    _convert_item: Callable[[object], object]

    def __init__(self, convert_item: Callable[[object], object]) -> None:
        """Инициализирует конвертер.

        :param convert_item: Функция, превращающая элемент в данные для JSON.
        :raises ArgumentsException: Если значение нельзя вызвать.
        """
        self._convert_item = CommonValidator.validate_callable(
            convert_item, "convert_item", "Ожидается функция конвертации элемента"
        )

    @override
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает список в словарь «наименование поля — список данных элементов».

        :param field: Наименование поля, ключ результата.
        :param value: Список или кортеж.
        :return: Словарь ``{field: [данные, ...]}``, порядок элементов сохраняется.
        :raises ArgumentsException: Если наименование поля некорректно, значение не список или кортеж
            либо элемент не удалось сконвертировать.
        """
        field = CommonValidator.validate_string(field, "field")
        if not isinstance(value, (list, tuple)):
            raise ArgumentsException("value", "Ожидается список или кортеж")

        items = cast(Sequence[object], value)
        # Рекурсия: функция конвертации — ConverterFactory.convert, она выберет конвертер элемента
        data = [self._convert_item(item) for item in items]
        return self._entry(field, data)
