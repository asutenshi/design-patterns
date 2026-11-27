from enum import Enum


class TableExportFormat(Enum):
    """Форматы табличной выгрузки данных: логов, ведомостей и журналов."""

    # Текстовый файл для просмотра в блокноте
    TXT = "txt"
    # Таблица CSV для открытия в Excel
    CSV = "csv"
    # Таблица Markdown для просмотра текстом в браузере
    MARKDOWN = "markdown"
