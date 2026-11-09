from collections.abc import Callable
from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator


class ListDeserializer(AbstractDeserializer):
    """Десериализатор списков: каждый элемент собирается функцией фабрики, порядок сохраняется.

    Функция — обычно ``DeserializerFactory._resolve``, поэтому в списке могут лежать и модели,
    и простые значения, и вложенные списки.
    """

    # Функция фабрики, превращающая значение из JSON в объект
    _resolve: Callable[[object], object]

    def __init__(self, resolve: Callable[[object], object]) -> None:
        """Инициализирует десериализатор.

        :param resolve: Функция, превращающая значение из JSON в объект.
        :raises ArgumentsException: Если значение нельзя вызвать.
        """
        self._resolve = CommonValidator.validate_callable(resolve, "resolve", "Ожидается функция десериализации")

    @override
    def deserialize(self, data: object) -> object:
        """Превращает список значений из JSON в список объектов.

        :param data: Список значений.
        :return: Новый список объектов в исходном порядке.
        :raises ArgumentsException: Если данные не список или элемент не собрался.
        :raises OperationException: Если элемент ссылается на модель, которой нет в данных.
        """
        items = cast(list[object], CommonValidator.validate_instance(data, list, "data", "Ожидается список"))
        # Рекурсия: функция фабрики выберет десериализатор для каждого элемента
        return [self._resolve(item) for item in items]
