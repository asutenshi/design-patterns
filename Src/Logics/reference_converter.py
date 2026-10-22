from collections.abc import Callable
from typing import override

from Src.Core.abstract_converter import AbstractConverter
from Src.Core.common_validator import CommonValidator


class ReferenceConverter(AbstractConverter):
    """Конвертер ссылок на модели: вложенный объект записывается вложенным словарём своих полей.

    Сам объект конвертер не разбирает, а передаёт функции раскрытия — обычно это
    ``ConverterFactory.convert``. Так вложенные модели на любой глубине обрабатываются
    тем же механизмом, а конвертер не зависит от класса фабрики.
    """

    # Функция, превращающая объект в словарь его полей
    _expand: Callable[[object], dict[str, object]]

    def __init__(self, expand: Callable[[object], dict[str, object]]) -> None:
        """Инициализирует конвертер.

        :param expand: Функция, превращающая объект в словарь его полей.
        :raises ArgumentsException: Если значение нельзя вызвать.
        """
        self._expand = CommonValidator.validate_callable(expand, "expand", "Ожидается функция раскрытия объекта")

    @override
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает вложенный объект в словарь «наименование поля — словарь полей объекта».

        :param field: Наименование поля, ключ результата.
        :param value: Вложенный объект с полями, например модель.
        :return: Словарь ``{field: {поле: данные, ...}}``.
        :raises ArgumentsException: Если наименование поля некорректно или функция раскрытия отвергла объект.
        """
        return self._entry(field, self._expand(value))
