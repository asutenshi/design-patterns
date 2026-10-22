from collections.abc import Callable, Sequence
from typing import cast, override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException


class CollectionConverter(AbstractConverter):
    """Конвертер списков: список или кортеж записывается списком данных элементов.

    Каждый элемент обрабатывается своим конвертером, который выбирает функция выбора —
    обычно это ``ConverterFactory.create``. Поэтому в одном списке могут лежать и строки, и модели.
    У элемента нет своего поля: он конвертируется под наименованием поля списка,
    а в результат попадают только его данные.
    """

    # Функция, выбирающая конвертер по значению элемента
    _create: Callable[[object], AbstractConverter]

    def __init__(self, create: Callable[[object], AbstractConverter]) -> None:
        """Инициализирует конвертер.

        :param create: Функция, выбирающая конвертер по значению элемента.
        :raises ArgumentsException: Если значение нельзя вызвать.
        """
        self._create = CommonValidator.validate_callable(create, "create", "Ожидается функция выбора конвертера")

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
        data = [self._create(item).convert(field, item)[field] for item in items]
        return self._entry(field, data)
