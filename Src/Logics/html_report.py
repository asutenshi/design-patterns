import xml.etree.ElementTree as ET
from typing import override

from Src.Core.abstract_report import AbstractReport
from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Dtos.report_result import ReportResult


class HtmlReport(AbstractReport):
    """Отчёт в формате HTML: самостоятельная страница с таблицей полей.

    Заголовок страницы — наименование сущности. Каждое поле — строка таблицы: имя в ``<th>``,
    значение в ``<td>``. Вложенный объект — вложенная таблица, список — нумерованный ``<ol>``.
    Ссылка на сущность выводится как ``наименование [код]``. Страницу собирает ElementTree
    в режиме HTML, он же экранирует значения. Правила обхода — в AbstractReport.

    Пример фрагмента отчёта по карте::

        <tr>
          <th>items</th>
          <td>
            <ol>
              <li>
                <table>
                  <tr>
                    <th>nomenclature</th>
                    <td>Свёкла [9a1b...]</td>
    """

    # Объявление типа документа
    _DOCTYPE: str = "<!DOCTYPE html>"
    # Оформление таблиц: рамки ячеек и выравнивание по верхнему краю
    _STYLE: str = (
        "table { border-collapse: collapse; } "
        "th, td { border: 1px solid #999; padding: 2px 6px; text-align: left; vertical-align: top; }"
    )
    # Отступ одного уровня вложенности
    _INDENT: str = "  "

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает False: отчёт отдаётся текстом."""
        return False

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип HTML в кодировке UTF-8."""
        return "text/html; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла HTML."""
        return "html"

    @override
    def build(self, source: NamedEntity) -> ReportResult:
        """Формирует отчёт HTML по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат с текстом страницы.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """
        source = CommonValidator.validate_instance(source, NamedEntity, "source", "Ожидается сущность с наименованием")
        page = ET.Element("html", lang="ru")
        head = ET.SubElement(page, "head")
        _ = ET.SubElement(head, "meta", charset="utf-8")
        ET.SubElement(head, "title").text = source.name
        ET.SubElement(head, "style").text = self._STYLE
        body = ET.SubElement(page, "body")
        ET.SubElement(body, "h1").text = source.name
        body.append(self._table(source))

        ET.indent(page, space=self._INDENT)
        return self._result(f"{self._DOCTYPE}\n{ET.tostring(page, encoding='unicode', method='html')}\n")

    def _table(self, source: object) -> ET.Element:
        """Возвращает таблицу полей раскрываемого объекта.

        :param source: Раскрываемый объект.
        :return: Элемент ``<table>``, по строке на поле.
        """
        table = ET.Element("table")
        for field, value in self._fields(source):
            row = ET.SubElement(table, "tr")
            ET.SubElement(row, "th").text = field
            self._fill_value(ET.SubElement(row, "td"), value)
        return table

    def _fill_value(self, element: ET.Element, value: object) -> None:
        """Записывает значение в ячейку таблицы или пункт списка.

        :param element: Элемент ``<td>`` или ``<li>``.
        :param value: Значение поля или элемент списка.
        """
        if isinstance(value, NamedEntity):
            element.text = self._format_reference(value)
        elif self._is_scalar(value):
            element.text = self._format_scalar(value)
        elif self._is_collection(value):
            items = ET.SubElement(element, "ol")
            for item in value:
                self._fill_value(ET.SubElement(items, "li"), item)
        else:
            element.append(self._table(value))
