from abc import ABC, abstractmethod

from Src.Core.common_validator import CommonValidator


class AbstractConverter(ABC):
    """Абстрактный конвертер: превращает значение поля в словарь «наименование поля — данные поля».

    У каждого вида значений свой наследник: простые значения, даты, ссылки на модели, списки, словари.
    Конвертер по типу значения выбирает фабрика ``ConverterFactory``, клиент работает только с ней.
    Данные — то, что ``json.dumps`` записывает без настроек: числа, строки, bool, None, списки и словари.
    """

    @abstractmethod
    def convert(self, field: str, value: object) -> dict[str, object]:
        """Превращает значение поля в словарь из одной пары «наименование поля — данные поля».

        :param field: Наименование поля, ключ результата.
        :param value: Значение поля любого типа.
        :return: Словарь ``{field: данные}``.
        :raises ArgumentsException: Если наименование поля некорректно или конвертер не обрабатывает такое значение.
        """

    @staticmethod
    def _entry(field: str, data: object) -> dict[str, object]:
        """Оформляет данные поля словарём с ключом — наименованием поля.

        :param field: Наименование поля.
        :param data: Данные поля.
        :return: Словарь ``{field: data}``, наименование очищено от пробелов по краям.
        :raises ArgumentsException: Если наименование не строка, пустое или состоит из пробелов.
        """
        return {CommonValidator.validate_string(field, "field"): data}
