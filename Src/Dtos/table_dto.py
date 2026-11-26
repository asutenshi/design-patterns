from typing import cast

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException


class TableDto:
    """Универсальная плоская таблица: заголовки колонок и строки текстовых значений.

    Отделяет подготовку данных конкретной предметной области от форматирования в TXT, CSV и Markdown,
    поэтому табличный экспорт переиспользуется для логов, ОСВ и других журналов.
    """

    # Названия колонок таблицы
    _headers: tuple[str, ...]
    # Строки таблицы с числом ячеек, равным числу заголовков
    _rows: tuple[tuple[str, ...], ...]

    def __init__(self, headers: list[str], rows: list[list[str]]) -> None:
        """Инициализирует таблицу.

        :param headers: Непустой список непустых названий колонок.
        :param rows: Список строк; длина каждой строки должна совпадать с числом колонок.
        :raises ArgumentsException: Если заголовки пусты, значения не строки или длина строки не совпадает.
        """
        raw_headers = cast(
            list[object], CommonValidator.validate_instance(headers, list, "headers", "Ожидается список заголовков")
        )
        if not raw_headers:
            raise ArgumentsException("headers", "Список заголовков не может быть пустым")
        validated_headers = tuple(CommonValidator.validate_string(item, "headers") for item in raw_headers)

        raw_rows = cast(list[object], CommonValidator.validate_instance(rows, list, "rows", "Ожидается список строк"))
        validated_rows: list[tuple[str, ...]] = []
        for raw_row in raw_rows:
            row = cast(list[object], CommonValidator.validate_instance(raw_row, list, "rows", "Ожидается строка-список"))
            if len(row) != len(validated_headers):
                raise ArgumentsException(
                    "rows", f"Ожидается колонок: {len(validated_headers)}, получено: {len(row)}"
                )
            cells = tuple(CommonValidator.validate_instance(cell, str, "rows", "Ячейка должна быть строкой") for cell in row)
            validated_rows.append(cells)

        self._headers = validated_headers
        self._rows = tuple(validated_rows)

    @property
    def headers(self) -> tuple[str, ...]:
        """Возвращает заголовки колонок таблицы."""
        return self._headers

    @property
    def rows(self) -> tuple[tuple[str, ...], ...]:
        """Возвращает строки таблицы."""
        return self._rows
