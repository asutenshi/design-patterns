from html.parser import HTMLParser
from typing import override

from Src.Dtos.report_result import ReportResult
from Src.Logics.html_report import HtmlReport
from Src.Logics.storage_manager import StorageManager
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel


class TextCollector(HTMLParser):
    """Собирает непустой текст элементов страницы вместе с именем элемента, в порядке появления."""

    def __init__(self) -> None:
        """Инициализирует пустой сборщик."""
        super().__init__()
        self.texts: list[tuple[str, str]] = []
        self._tag: str = ""

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Запоминает элемент, текст которого может идти следом."""
        self._tag = tag

    @override
    def handle_data(self, data: str) -> None:
        """Сохраняет текст текущего элемента, пробелы форматирования пропускает."""
        if data.strip():
            self.texts.append((self._tag, data.strip()))


def collect(text: str) -> list[tuple[str, str]]:
    """Возвращает пары «элемент — текст» страницы."""
    collector = TextCollector()
    collector.feed(text)
    return collector.texts


def find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


def test_build_derived_range_returns_page_with_table_row_per_field(first_start_storage: StorageManager):
    """Страница — заголовок с наименованием и таблица: имя поля в th, значение в td, ссылка с кодом."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    result = HtmlReport().build(kilogram)

    # Проверка
    assert isinstance(result, ReportResult)
    assert result.text.startswith("<!DOCTYPE html>\n<html lang=\"ru\">")
    assert [pair for pair in collect(result.text) if pair[0] != "style"] == [
        ("title", "килограмм"),
        ("h1", "килограмм"),
        ("th", "id"),
        ("td", str(kilogram.id)),
        ("th", "name"),
        ("td", "килограмм"),
        ("th", "base"),
        ("td", f"грамм [{kilogram.base.id}]"),
        ("th", "factor"),
        ("td", "1000"),
        ("th", "is_base"),
        ("td", "False"),
    ]


def test_build_recipe_lists_steps_and_items_in_ordered_lists(first_start_storage: StorageManager):
    """Шаги — пункты li по порядку, ингредиенты — вложенные таблицы, по одной ссылке на номенклатуру в каждой."""
    # Подготовка
    recipe = find_recipe(first_start_storage, "Зажарка свекольная")

    # Действие
    texts = collect(HtmlReport().build(recipe).text)

    # Проверка
    assert [text for tag, text in texts if tag == "li"] == recipe.steps
    nomenclatures = [texts[index + 1] for index, pair in enumerate(texts) if pair == ("th", "nomenclature")]
    assert nomenclatures == [("td", f"{item.nomenclature.name} [{item.nomenclature.id}]") for item in recipe.items]


def test_build_name_with_markup_chars_is_escaped():
    """Символы разметки HTML в значении экранируются и показываются как текст."""
    # Подготовка
    unit = RangeModel("<b>кг</b> & г", 1)

    # Действие
    text = HtmlReport().build(unit).text

    # Проверка
    assert "<b>" not in text
    assert "&lt;b&gt;кг&lt;/b&gt; &amp; г" in text
    assert ("h1", "<b>кг</b> & г") in collect(text)
