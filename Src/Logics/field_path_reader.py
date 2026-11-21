from typing import cast

from Src.Core.common import Common
from Src.Core.exception import ArgumentsException


class FieldPathReader:
    """Читает значения поля модели по пути через точку, например ``range.base.name``.

    Читать можно только публичные свойства (``Common.get_fields``), поэтому новой модели
    ничего объявлять не нужно, а приватные атрибуты и методы клиенту недоступны.
    Если на пути встречается коллекция (список или кортеж), чтение продолжается для каждого её элемента.
    """

    def read(self, source: object, path: str) -> list[object]:
        """Возвращает все значения, найденные по пути.

        :param source: Объект, с которого начинается путь.
        :param path: Путь к полю через точку.
        :return: Значения в порядке обхода. Без коллекций на пути значение одно,
            для пустой коллекции результат пуст.
        :raises ArgumentsException: Если шаг пути не является публичным свойством текущего объекта.
        """
        return self._walk(source, path.split("."))

    def _read_field(self, source: object, field: str) -> object:
        """Читает одно публичное свойство объекта.

        :param source: Объект, у которого читается свойство.
        :param field: Имя свойства.
        :return: Значение свойства.
        :raises ArgumentsException: Если такого публичного свойства у объекта нет.
        """
        if field not in Common.get_fields(source):
            raise ArgumentsException("field", f"Поле недоступно: {field}")
        return cast(object, getattr(source, field))

    def _walk(self, value: object, steps: list[str]) -> list[object]:
        """Проходит оставшиеся шаги пути от значения и собирает найденные значения.

        Коллекция шаг не тратит: тот же остаток пути применяется к каждому её элементу.

        :param value: Текущее значение на пути.
        :param steps: Оставшиеся шаги пути.
        :return: Значения, найденные в конце пути.
        :raises ArgumentsException: Если шаг пути не является публичным свойством текущего объекта.
        """
        if isinstance(value, (list, tuple)):
            values: list[object] = []
            for item in cast(list[object] | tuple[object, ...], value):
                values.extend(self._walk(item, steps))
            return values

        if steps:
            return self._walk(self._read_field(value, steps[0]), steps[1:])
        return [value]
