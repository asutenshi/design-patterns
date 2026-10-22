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
from Src.Logics.reference_converter import ReferenceConverter


class ConverterFactory:
    """Фабрика конвертеров: превращает любой объект во вложенный словарь его полей.

    Клиент вызывает только ``convert(source)``. Для каждого поля объекта фабрика выбирает конвертер
    по типу значения (``create()``) и объединяет полученные словари «наименование поля — данные».
    Конвертеры ссылок и списков возвращают вложенные объекты обратно в фабрику, поэтому словарь
    собирается рекурсивно на любую глубину. Результат сразу записывается ``json.dumps``.

    Проектные решения:

    - Конвертер выбирается по сопоставлению «тип — конвертер» с обходом MRO типа значения, без проверок
      ``isinstance`` по цепочке: ``bool`` находится через ``int``, ``datetime`` — через ``date``,
      любое перечисление — через ``Enum``, а всё прочее (модели) — через ``object``.
      Новый вид значений подключается строкой в ``_converters``.
    - Поля объекта — его публичные свойства (``Common.get_fields``), как и в отчётах. Поэтому в словарь
      попадают и вычисляемые свойства (``is_base``, веса): отличить их от данных в общем случае нельзя.
    - Защита от циклов: фабрика помнит путь от корня до текущего объекта. Объект, который уже есть
      на пути (у базовой единицы ``RangeModel.base`` — она сама), записывается ссылкой ``{"id": ...}``.
      Проверяется только путь, поэтому общая модель (одна группа у разных позиций) раскрывается
      везде целиком. Из-за пути фабрика хранит состояние и не годится для параллельных вызовов.
    - Конвертеры не хранят состояния, поэтому фабрика создаёт их один раз и выдаёт по типу значения.
    """

    # Сопоставление типа значения и конвертера
    _converters: dict[type, AbstractConverter]
    # Конвертер моделей, им же обрабатываются типы без своего конвертера
    _reference: ReferenceConverter
    # Объекты, которые раскрываются сейчас: путь от корня до текущего объекта
    _path: list[object]

    def __init__(self) -> None:
        """Инициализирует фабрику и её конвертеры."""
        basic = BasicConverter()
        collection = CollectionConverter(self.create)
        self._reference = ReferenceConverter(self.convert)
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
            object: self._reference,
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
        return self._reference

    def convert(self, source: object) -> dict[str, object]:
        """Превращает объект в словарь «наименование поля — данные поля», вложенные объекты — рекурсивно.

        :param source: Объект с полями: модель, хранилище и т. п.
        :return: Словарь полей в порядке объявления, сначала поля базовых классов.
        :raises ArgumentsException: Если source — простое значение, дата или список: у них нет полей.
        :raises OperationException: Если объект без идентификатора ссылается сам на себя.
        """
        if self.create(source) is not self._reference:
            raise ArgumentsException("source", "Ожидается объект с полями, а не простое значение, дата или список")
        if any(item is source for item in self._path):
            return self._cycle_reference(source)

        self._path.append(source)
        try:
            result: dict[str, object] = {}
            for field in Common.get_fields(source):
                value = cast(object, getattr(source, field))
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

        return self.create(source.id).convert("id", source.id)
