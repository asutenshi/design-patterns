from enum import Enum

import pytest
from Src.Core.abstract_report import AbstractReport
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.exception import ArgumentsException
from Src.Core.response_format import ResponseFormat
from Src.Logics.report_factory import ReportFactory
from Src.Logics.txt_report import TxtReport


class OtherFormat(Enum):
    """Перечисление, похожее на ResponseFormat, но им не являющееся."""

    TXT = "txt"


def test_create_txt_returns_txt_report():
    """Для формата TXT фабрика возвращает TxtReport."""
    # Подготовка
    factory = ReportFactory()

    # Действие
    report = factory.create(ResponseFormat.TXT)

    # Проверка
    assert isinstance(factory, AbstractReportFactory)
    assert type(report) is TxtReport


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_create_every_format_returns_report(response_format: ResponseFormat):
    """Для каждого формата из ResponseFormat в фабрике есть реализация: новый формат нельзя забыть подключить."""
    # Действие
    report = ReportFactory().create(response_format)

    # Проверка
    assert isinstance(report, AbstractReport)


def test_create_returns_new_report_each_time():
    """Каждый вызов create создаёт новый отчёт."""
    # Подготовка
    factory = ReportFactory()

    # Действие
    first = factory.create(ResponseFormat.TXT)
    second = factory.create(ResponseFormat.TXT)

    # Проверка
    assert first is not second


# Подготовка
@pytest.mark.parametrize("response_format", ["txt", OtherFormat.TXT, None])
def test_create_not_response_format_raises_arguments_exception(response_format: object):
    """Значение, не являющееся ResponseFormat, отвергается, даже если совпадает его строковое значение."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportFactory().create(response_format)  # pyright: ignore[reportArgumentType]


def test_create_format_without_report_raises_arguments_exception(monkeypatch: pytest.MonkeyPatch):
    """Для формата, которого нет в сопоставлении фабрики, бросается ArgumentsException."""
    # Подготовка
    monkeypatch.setattr(ReportFactory, "_reports", {})

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportFactory().create(ResponseFormat.TXT)
