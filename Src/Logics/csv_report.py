import csv
import io
from typing import ClassVar, override

from Src.Core.abstract_report import AbstractReport
from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Dtos.report_result import ReportResult


class CsvReport(AbstractReport):
    """Отчёт в формате CSV: таблица из двух колонок «поле» и «значение».

    Дерево сущности разворачивается в строки: каждому простому значению и ссылке —
    своя строка с путём к нему. Путь вложенного поля пишется через точку, элемента списка —
    номером в квадратных скобках с единицы (как пункты в Markdown). Пустой список
    и объект без полей дают строку с пустым значением, чтобы поле не пропало из таблицы.
    Ссылка на сущность выводится как ``наименование [код]``. Правила обхода — в AbstractReport.

    Разделитель — точка с запятой: так файл без настройки открывается в Excel с русской локалью,
    где запятая служит десятичным разделителем. Кавычки и переводы строк экранирует модуль csv.

    Байты результата начинаются с метки порядка байтов UTF-8: без неё Excel открывает файл
    в кодировке системы и кириллица превращается в «кракозябры». Текст метки не содержит.

    Пример фрагмента отчёта по карте::

        field;value
        name;Зажарка свекольная
        items[1].nomenclature;Свёкла [9a1b...]
        items[1].quantity;400
    """

    # UTF-8 с меткой порядка байтов
    _ENCODING: ClassVar[str] = "utf-8-sig"
    # Разделитель колонок
    _DELIMITER: str = ";"
    # Заголовок таблицы
    _HEADER: tuple[str, str] = ("field", "value")

    @property
    @override
    def is_binary(self) -> bool:
        """Возвращает True: отчёт отдаётся файлом на скачивание."""
        return True

    @property
    @override
    def media_type(self) -> str:
        """Возвращает MIME-тип CSV в кодировке UTF-8."""
        return "text/csv; charset=utf-8"

    @property
    @override
    def file_extension(self) -> str:
        """Возвращает расширение файла CSV."""
        return "csv"

    @override
    def build(self, source: NamedEntity) -> ReportResult:
        """Формирует отчёт CSV по сущности.

        :param source: Сущность, по которой строится отчёт: сама она раскрывается целиком.
        :return: Результат с текстом таблицы.
        :raises ArgumentsException: Если source не является сущностью с наименованием.
        """
        source = CommonValidator.validate_instance(source, NamedEntity, "source", "Ожидается сущность с наименованием")
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=self._DELIMITER)
        writer.writerow(self._HEADER)
        writer.writerows(self._object_rows(source, ""))
        return self._result(buffer.getvalue())

    def _object_rows(self, source: object, path: str) -> list[tuple[str, str]]:
        """Возвращает строки всех полей раскрываемого объекта.

        :param source: Раскрываемый объект.
        :param path: Путь к объекту, пустая строка — корень отчёта.
        :return: Пары «путь — значение».
        """
        rows: list[tuple[str, str]] = []
        for field, value in self._fields(source):
            rows.extend(self._value_rows(f"{path}.{field}" if path else field, value))
        return rows

    def _value_rows(self, path: str, value: object) -> list[tuple[str, str]]:
        """Возвращает строки одного значения: простое значение и ссылка — одной строкой, остальное — по элементам.

        :param path: Путь к значению.
        :param value: Значение поля или элемент списка.
        :return: Пары «путь — значение».
        """
        if isinstance(value, NamedEntity):
            return [(path, self._format_reference(value))]
        if self._is_scalar(value):
            return [(path, self._format_scalar(value))]

        rows: list[tuple[str, str]] = []
        if self._is_collection(value):
            for number, element in enumerate(value, start=1):
                rows.extend(self._value_rows(f"{path}[{number}]", element))
        else:
            rows = self._object_rows(value, path)
        return rows or [(path, "")]
