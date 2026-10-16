from typing import override

from Src.Core.abstract_report import AbstractReport
from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Dtos.markdown_report_result import MarkdownReportResult


class MarkdownReport(AbstractReport):
    """Отчёт в формате Markdown (CommonMark).

    Заголовок — наименование сущности, под ним маркированный список полей ``- **имя**: значение``.
    Вложенный объект и список выводятся вложенным списком под строкой ``- **имя**:``,
    элементы списка нумеруются. Поля элемента-объекта идут вложенным маркированным списком,
    первое — на строке номера. Ссылка на сущность выводится как ``наименование (`код`)``.
    Служебные символы Markdown в значениях экранируются. Правила обхода — в AbstractReport.

    Пример фрагмента отчёта по карте::

        # Зажарка свекольная

        - **name**: Зажарка свекольная
        - **items**:
          1. - **nomenclature**: Свёкла (`9a1b...`)
             - **quantity**: 400
    """

    # Отступ вложенного списка под маркером «- »
    _INDENT: str = "  "
    # Символы, которые Markdown может принять за разметку
    _SPECIAL_CHARS: str = "\\`*_[]<>#"

    @override
    def build(self, source: NamedEntity) -> MarkdownReportResult:
        """Формирует отчёт Markdown по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат с текстом документа.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """
        source = CommonValidator.validate_instance(source, NamedEntity, "source", "Ожидается сущность с наименованием")
        lines = [f"# {self._escape(source.name)}", "", *self._object_lines(source)]
        return MarkdownReportResult("\n".join(lines) + "\n")

    def _object_lines(self, source: object) -> list[str]:
        """Возвращает маркированный список полей раскрываемого объекта.

        :param source: Раскрываемый объект.
        :return: Строки списка без отступа, вложенные уровни — с отступом относительно них.
        """
        lines: list[str] = []
        for field, value in self._fields(source):
            if self._is_scalar(value) or self._is_reference(value):
                lines.append(f"- **{field}**: {self._value_text(value)}")
                continue

            lines.append(f"- **{field}**:")
            nested = self._list_lines(value) if self._is_collection(value) else self._object_lines(value)
            lines.extend(f"{self._INDENT}{line}" for line in nested)
        return lines

    def _list_lines(self, elements: object) -> list[str]:
        """Возвращает нумерованный список элементов.

        Строки элемента-объекта после первой выравниваются по тексту после номера:
        так они остаются внутри пункта списка.

        :param elements: Список или кортеж элементов.
        :return: Строки списка без отступа.
        """
        lines: list[str] = []
        if not self._is_collection(elements):
            return lines
        for number, element in enumerate(elements, start=1):
            marker = f"{number}. "
            if self._is_scalar(element) or self._is_reference(element):
                lines.append(f"{marker}{self._value_text(element)}")
                continue

            nested = self._object_lines(element)
            if not nested:
                lines.append(marker.rstrip())
                continue
            lines.append(f"{marker}{nested[0]}")
            lines.extend(f"{' ' * len(marker)}{line}" for line in nested[1:])
        return lines

    def _value_text(self, value: object) -> str:
        """Возвращает текст простого значения или ссылки на сущность с экранированной разметкой.

        :param value: Простое значение или сущность с наименованием.
        :return: Значение строкой, для сущности — ``наименование (`код`)``.
        """
        if isinstance(value, NamedEntity):
            return f"{self._escape(value.name)} (`{value.id}`)"
        return self._escape(self._format_scalar(value))

    def _escape(self, text: str) -> str:
        """Экранирует обратной косой чертой символы, которые Markdown может принять за разметку.

        :param text: Исходный текст.
        :return: Текст, который отображается как есть.
        """
        return "".join(f"\\{char}" if char in self._SPECIAL_CHARS else char for char in text)
