import uuid
from datetime import date
from enum import Enum
from types import NoneType
from typing import cast

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.base_entity import BaseEntity
from Src.Core.common import Common
from Src.Core.exception import ArgumentsException, OperationException
from Src.Logics.basic_converter import BasicConverter
from Src.Logics.collection_converter import CollectionConverter
from Src.Logics.datetime_converter import DatetimeConverter
from Src.Logics.dict_converter import DictConverter
from Src.Logics.reference_converter import ReferenceConverter

# Служебное наименование поля для значения верхнего уровня: у него своего поля нет
_ROOT_FIELD = "value"


class ConverterFactory:
    """Фабрика конвертеров: превращает любой объект в данные, которые ``json.dumps`` записывает без настроек.

    Клиент вызывает только ``convert(source)``. Форма результата повторяет исходную структуру:
    модель — словарь «наименование поля — данные поля», список моделей — список словарей,
    словарь — словарь, простое значение — само значение, дата — строка ISO 8601.

    Проектные решения:

    - Конвертер выбирается по сопоставлению «тип — конвертер» с обходом MRO типа значения, без проверок
      ``isinstance`` по цепочке: ``bool`` находится через ``int``, ``datetime`` — через ``date``,
      любое перечисление — через ``Enum``, а всё прочее (модели) — через ``object``.
      Новый вид значений подключается строкой в ``_converters``.
    - Конвертеры возвращают ``{поле: данные}``, а у значения верхнего уровня поля нет. Поэтому ``convert``
      передаёт конвертеру служебное наименование ``_ROOT_FIELD`` и сразу снимает его с результата.
    - Рекурсия идёт через функции, которые фабрика передаёт конвертерам: ``ReferenceConverter`` получает
      ``_fields``, ``CollectionConverter`` и ``DictConverter`` — ``convert``. Конвертеры не зависят
      от класса фабрики, а словарь собирается на любую глубину.
    - Поля объекта — его публичные свойства (``Common.get_fields``), как и в отчётах. Поэтому в словарь
      попадают и вычисляемые свойства (``is_base``, веса): отличить их от данных в общем случае нельзя.
      Объект без публичных свойств (функция, множество) — ошибка: пустой словарь молча потерял бы данные.
    - Защита от циклов: фабрика помнит путь от корня до текущего объекта. Объект, который уже есть
      на пути (у базовой единицы ``RangeModel.base`` — она сама), записывается ссылкой ``{"id": ...}``.
      Проверяется только путь, поэтому общая модель (одна группа у разных позиций) раскрывается
      везде целиком. Из-за пути фабрика хранит состояние и не годится для параллельных вызовов.
    - Конвертеры не хранят состояния, поэтому фабрика создаёт их один раз и выдаёт по типу значения.
    """

    # Сопоставление типа значения и конвертера, под ``object`` — конвертер моделей и прочих типов
    _converters: dict[type, AbstractConverter]
    # Объекты, которые раскрываются сейчас: путь от корня до текущего объекта
    _path: list[object]

    def __init__(self) -> None:
        """Инициализирует фабрику и её конвертеры."""
        basic = BasicConverter()
        collection = CollectionConverter(self.convert)
        self._converters = {
            str: basic,
            int: basic,
            float: basic,
            NoneType: basic,
            Enum: basic,
            uuid.UUID: basic,
            date: DatetimeConverter(),
            list: collection,
            tuple: collection,
            dict: DictConverter(self.convert),
            object: ReferenceConverter(self._fields),
        }
        self._path = []

    def create(self, value: object) -> AbstractConverter:
        """Выбирает конвертер по типу значения.

        Типы проверяются от класса значения к его базовым классам, побеждает первый найденный.

        :param value: Значение любого типа.
        :return: Конвертер для этого значения, для моделей — конвертер ссылок.
        """
        for klass in type(value).__mro__:
            converter = self._converters.get(klass)
            if converter is not None:
                return converter
        # Сюда не дойти: object есть в MRO любого типа и в сопоставлении
        return self._converters[object]

    def convert(self, source: object) -> object:
        """Превращает любой объект в данные для JSON, вложенные объекты — рекурсивно.

        :param source: Объект любого типа: модель, хранилище, список, словарь, дата, простое значение.
        :return: Для модели — словарь полей в порядке объявления, для списка — список, для словаря — словарь,
            для даты — строка ISO 8601, для простого значения — оно само.
        :raises ArgumentsException: Если в структуре есть объект без публичных свойств (функция, множество)
            или словарь с нестроковым ключом.
        :raises OperationException: Если объект без идентификатора ссылается сам на себя.
        """
        return self.create(source).convert(_ROOT_FIELD, source)[_ROOT_FIELD]

    def _fields(self, source: object) -> dict[str, object]:
        """Превращает объект в словарь «наименование поля — данные поля».

        :param source: Объект с публичными свойствами: модель, хранилище и т. п.
        :return: Словарь полей в порядке объявления, сначала поля базовых классов.
        :raises ArgumentsException: Если у объекта нет публичных свойств или поле не удалось сконвертировать.
        :raises OperationException: Если объект без идентификатора ссылается сам на себя.
        """
        fields = Common.get_fields(source)
        if not fields:
            raise ArgumentsException("source", f"Ожидается объект с публичными свойствами: {type(source).__name__}")
        if any(item is source for item in self._path):
            return self._cycle_reference(source)

        self._path.append(source)
        try:
            result: dict[str, object] = {}
            for field in fields:
                value = cast(object, getattr(source, field))
                # Рекурсия: для вложенной модели ReferenceConverter снова вызовет self._fields,
                # для списка и словаря их конвертеры вызовут self.convert для каждого элемента
                result.update(self.create(value).convert(field, value))
            return result
        finally:
            del self._path[-1]

    def _cycle_reference(self, source: object) -> dict[str, object]:
        """Возвращает ссылку на объект, который уже раскрывается выше по пути.

        :param source: Объект, замыкающий цикл.
        :return: Словарь ``{"id": код}``.
        :raises OperationException: Если у объекта нет идентификатора и сослаться на него нельзя.
        """
        if not isinstance(source, BaseEntity):
            raise OperationException(f"Циклическая ссылка на объект без идентификатора: {type(source).__name__}")

        return {"id": self.convert(source.id)}
