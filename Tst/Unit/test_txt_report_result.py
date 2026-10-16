import pytest
from Src.Core.exception import ArgumentsException
from Src.Dtos.txt_report_result import TxtReportResult


def test_init_text_returns_text_and_utf8_binary():
    """Текст отдаётся как есть, байты — тот же текст в UTF-8."""
    # Подготовка
    text = "name: Борщ"

    # Действие
    result = TxtReportResult(text)

    # Проверка
    assert result.text == text
    assert result.binary == text.encode("utf-8")


def test_init_empty_text_is_allowed():
    """Пустой отчёт допустим: данных может не быть."""
    # Действие
    result = TxtReportResult("")

    # Проверка
    assert result.text == ""
    assert result.binary == b""


def test_is_binary_returns_false_and_media_type_is_plain_text():
    """Текстовый результат отдаётся текстом с типом text/plain в UTF-8 и расширением txt."""
    # Подготовка
    result = TxtReportResult("текст")

    # Действие и проверка
    assert result.is_binary is False
    assert result.media_type == "text/plain; charset=utf-8"
    assert result.file_extension == "txt"


# Подготовка
@pytest.mark.parametrize("text", [None, 1, b"bytes", ["строка"]])
def test_init_not_string_raises_arguments_exception(text: object):
    """Содержимое, не являющееся строкой, отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = TxtReportResult(text)  # pyright: ignore[reportArgumentType]


def test_eq_same_text_results_are_equal_and_have_same_hash():
    """Результаты с одинаковым содержимым равны и одинаково хэшируются: это объекты-значения."""
    # Подготовка
    first = TxtReportResult("отчёт")
    second = TxtReportResult("отчёт")

    # Действие и проверка
    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_eq_different_text_results_are_not_equal():
    """Результаты с разным содержимым не равны."""
    # Действие и проверка
    assert TxtReportResult("отчёт 1") != TxtReportResult("отчёт 2")


def test_eq_result_and_other_type_are_not_equal():
    """Результат не равен значению другого типа, даже если совпадает текст."""
    # Действие и проверка
    assert TxtReportResult("отчёт") != "отчёт"
