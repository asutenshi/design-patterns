from typing import override

from Src.Core.abstract_report import AbstractReport
from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Dtos.report_result import ReportResult


class TxtReport(AbstractReport):
    """Отчёт в формате простого текста.

    Каждое поле — строка ``имя: значение``. Вложенный объект и список выводятся под строкой
    ``имя:`` с отступом, элемент списка начинается с ``- ``. Ссылка на сущность выводится
    как ``наименование [код]``. Правила обхода — в AbstractReport.

    Пример фрагмента отчёта по карте::

        name: Зажарка свекольная
        result: Зажарка свекольная [3f2c...]
        items:
          - nomenclature: Свёкла [9a1b...]
            quantity: 400
    """

    # Отступ одного уровня вложенности
    _INDENT: str = "  "
    # Начало элемента списка
    _BULLET: str = "- "

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: отчёт отдаётся текстом."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип простой текст в кодировке UTF-8."""
        return "text/plain; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла простой текст."""
        return "txt"

    @override
    def build(self, source: NamedEntity) -> ReportResult:
        """Формирует текстовый отчёт по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат с текстом отчёта.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """
        source = CommonValidator.validate_instance(source, NamedEntity, "source", "Ожидается сущность с наименованием")
        return self._result("\n".join(self._object_lines(source, 0)))

    def _object_lines(self, source: object, level: int) -> list[str]:
        """Возвращает строки всех полей раскрываемого объекта.

        :param source: Раскрываемый объект.
        :param level: Уровень вложенности.
        :return: Строки отчёта.
        """
        lines: list[str] = []
        for field, value in self._fields(source):
            lines.extend(self._field_lines(field, value, level))
        return lines

    def _field_lines(self, field: str, value: object, level: int) -> list[str]:
        """Возвращает строки одного поля: простое значение и ссылка — одной строкой, остальное — под заголовком.

        :param field: Имя поля.
        :param value: Значение поля.
        :param level: Уровень вложенности поля.
        :return: Строки отчёта.
        """
        indent = self._INDENT * level
        if self._is_scalar(value) or self._is_reference(value):
            return [f"{indent}{field}: {self._value_text(value)}"]

        lines = [f"{indent}{field}:"]
        if self._is_collection(value):
            for element in value:
                lines.extend(self._element_lines(element, level + 1))
        else:
            lines.extend(self._object_lines(value, level + 1))
        return lines

    def _element_lines(self, element: object, level: int) -> list[str]:
        """Возвращает строки элемента списка: первая начинается с маркера, остальные выровнены под ней.

        :param element: Элемент списка.
        :param level: Уровень вложенности элемента.
        :return: Строки отчёта.
        """
        indent = self._INDENT * level
        if self._is_scalar(element) or self._is_reference(element):
            return [f"{indent}{self._BULLET}{self._value_text(element)}"]

        # Поля элемента выравниваются по тексту после маркера, а первое поле встаёт на строку маркера
        lines = self._object_lines(element, level + 1)
        if not lines:
            return [f"{indent}{self._BULLET}".rstrip()]
        lines[0] = f"{indent}{self._BULLET}{lines[0].lstrip()}"
        return lines

    def _value_text(self, value: object) -> str:
        """Возвращает текст простого значения или ссылки на сущность.

        :param value: Простое значение или сущность с наименованием.
        :return: Значение строкой, для сущности — ``наименование [код]``.
        """
        if isinstance(value, NamedEntity):
            return self._format_reference(value)
        return self._format_scalar(value)
