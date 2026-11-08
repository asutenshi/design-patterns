from typing import override

from Src.Core.abstract_deserializer import AbstractDeserializer


class BasicDeserializer(AbstractDeserializer):
    """Десериализатор простых значений: строка, число, bool и None переносятся как есть.

    Перечисления и даты в JSON — тоже строки. Во что их превратить, знает только модель,
    поэтому преобразование делает её ``from_dict``, а не десериализатор.
    """

    @override
    def deserialize(self, data: object) -> object:
        """Возвращает простое значение без изменений.

        :param data: Строка, число, bool или None.
        :return: То же значение.
        """
        return data
