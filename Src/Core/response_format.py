from enum import Enum


class ResponseFormat(Enum):
    """Формат, в котором формируется отчёт.

    Значения — строки: в таком виде формат задаётся в параметре запроса API и в файле настроек.
    """

    # Простой текст
    TXT = "txt"
    # Разметка Markdown
    MARKDOWN = "markdown"
    # Таблица CSV
    CSV = "csv"
    # Документ XML
    XML = "xml"
    # Страница HTML
    HTML = "html"
