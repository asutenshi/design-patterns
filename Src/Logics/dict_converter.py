from collections.abc import Callable, Mapping
from typing import cast, override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException


class DictConverter(AbstractConverter):
    """Конвертер словарей: словарь записывается словарём с теми же ключами и данными значений.

    Каждое значение превращается в данные функцией конвертации — обычно это ``ConverterFactory.convert``.
    Поэтому в значениях могут лежать и строки, и модели, и вложенные словари.
    Ключи переносятся как есть и должны быть строками: других ключей JSON не знает.
    """

    # Функция, превращающая значение в данные для JSON
    _convert_value: Callable[[object], object]

    def __init__(self, convert_value: Callable[[object], object]) -> None:
        """Инициализирует конвертер.

        :param convert_value: Функция, превращающая значение в данные для JSON.
        :raises ArgumentsException: Если значение нельзя вызвать.
        """
        self._convert_value = CommonValidator.validate_callable(
            convert_value, "convert_value", "Ожидается функция конвертации значения"
        )

    @override
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает словарь в словарь «наименование поля — словарь данных значений».

        :param field: Наименование поля, ключ результата.
        :param value: Словарь со строковыми ключами.
        :return: Словарь ``{field: {ключ: данные, ...}}``, порядок ключей сохраняется.
        :raises ArgumentsException: Если наименование поля некорректно, значение не словарь, ключ не строка
            либо значение не удалось сконвертировать.
        """
        field = CommonValidator.validate_string(field, "field")
        if not isinstance(value, dict):
            raise ArgumentsException("value", "Ожидается словарь")

        mapping = cast(Mapping[object, object], value)
        data: dict[str, object] = {}
        for key, item in mapping.items():
            if not isinstance(key, str):
                raise ArgumentsException("value", f"Ключ словаря должен быть строкой: {key!r}")
            # Рекурсия: функция конвертации — ConverterFactory.convert, она выберет конвертер значения
            data[key] = self._convert_value(item)
        return self._entry(field, data)
