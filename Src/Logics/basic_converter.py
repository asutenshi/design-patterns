import uuid
from enum import Enum
from typing import override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.exception import ArgumentsException


class BasicConverter(AbstractConverter):
    """Конвертер простых значений: тех, что JSON записывает без вложенности.

    Числа, строки, bool и None переносятся как есть. Перечисление заменяется своим значением,
    UUID — строкой: сами они в JSON не записываются, а их значения — простые.
    """

    @override
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает простое значение поля в словарь «наименование поля — значение».

        :param field: Наименование поля, ключ результата.
        :param value: Число, строка, bool, None, перечисление или UUID.
        :return: Словарь ``{field: значение}``.
        :raises ArgumentsException: Если наименование поля некорректно или значение не простое.
        """
        if isinstance(value, Enum):
            data: object = value.value  # pyright: ignore[reportAny]
        elif isinstance(value, uuid.UUID):
            data = str(value)
        elif value is None or isinstance(value, (str, int, float)):
            data = value
        else:
            raise ArgumentsException("value", "Ожидается число, строка, bool, None, перечисление или UUID")

        return self._entry(field, data)
