import xml.etree.ElementTree as ET
from typing import override

from Src.Core.abstract_report import AbstractReport
from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Dtos.xml_report_result import XmlReportResult


class XmlReport(AbstractReport):
    """Отчёт в формате XML.

    Корневой элемент назван по классу сущности, каждое поле — дочерний элемент с именем поля.
    Простое значение — текст элемента, ссылка на сущность — наименование в тексте и код
    в атрибуте ``id``. Элементы списка — дочерние элементы ``item``, вложенный объект —
    дочерние элементы полей. Документ собирает ElementTree, он же экранирует значения.
    Правила обхода — в AbstractReport.

    Пример фрагмента отчёта по карте::

        <RecipeModel>
          <name>Зажарка свекольная</name>
          <items>
            <item>
              <nomenclature id="9a1b...">Свёкла</nomenclature>
              <quantity>400</quantity>
    """

    # Объявление XML в начале документа
    _DECLARATION: str = '<?xml version="1.0" encoding="UTF-8"?>'
    # Имя элемента списка
    _ITEM_TAG: str = "item"
    # Отступ одного уровня вложенности
    _INDENT: str = "  "

    @override
    def build(self, source: NamedEntity) -> XmlReportResult:
        """Формирует отчёт XML по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат с текстом документа.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """
        source = CommonValidator.validate_instance(source, NamedEntity, "source", "Ожидается сущность с наименованием")
        root = ET.Element(type(source).__name__)
        self._fill_object(root, source)
        ET.indent(root, space=self._INDENT)
        return XmlReportResult(f"{self._DECLARATION}\n{ET.tostring(root, encoding='unicode')}\n")

    def _fill_object(self, element: ET.Element, source: object) -> None:
        """Добавляет в элемент дочерние элементы всех полей объекта.

        :param element: Элемент раскрываемого объекта.
        :param source: Раскрываемый объект.
        """
        for field, value in self._fields(source):
            self._fill_value(ET.SubElement(element, field), value)

    def _fill_value(self, element: ET.Element, value: object) -> None:
        """Записывает значение в элемент.

        :param element: Элемент поля или элемента списка.
        :param value: Значение поля или элемент списка.
        """
        if isinstance(value, NamedEntity):
            element.set("id", str(value.id))
            element.text = value.name
        elif self._is_scalar(value):
            element.text = self._format_scalar(value)
        elif self._is_collection(value):
            for item in value:
                self._fill_value(ET.SubElement(element, self._ITEM_TAG), item)
        else:
            self._fill_object(element, value)
