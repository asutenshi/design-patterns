from enum import Enum

import pytest
from Src.Core.abstract_report import AbstractReport
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.exception import ArgumentsException
from Src.Core.ownership_form import OwnershipForm
from Src.Core.response_format import ResponseFormat
from Src.Logics.csv_report import CsvReport
from Src.Logics.html_report import HtmlReport
from Src.Logics.markdown_report import MarkdownReport
from Src.Logics.report_factory import ReportFactory
from Src.Logics.txt_report import TxtReport
from Src.Logics.xml_report import XmlReport
from Src.Models.organization_model import OrganizationModel
from Src.Models.settings_model import SettingsModel


class OtherFormat(Enum):
    """Перечисление, похожее на ResponseFormat, но им не являющееся."""

    TXT = "txt"


def _settings(response_format: ResponseFormat = ResponseFormat.TXT) -> SettingsModel:
    """Создаёт корректные настройки с указанным форматом отчётов."""
    organization = OrganizationModel("Ромашка", "1234567894", "123456789", "12345678901234567890", OwnershipForm.LLC)
    return SettingsModel(organization, "Иванов И. И.", "Петрова А. А.", response_format=response_format)


# Подготовка
@pytest.mark.parametrize(
    ("response_format", "report_type"),
    [
        (ResponseFormat.TXT, TxtReport),
        (ResponseFormat.MARKDOWN, MarkdownReport),
        (ResponseFormat.CSV, CsvReport),
        (ResponseFormat.XML, XmlReport),
        (ResponseFormat.HTML, HtmlReport),
    ],
    ids=lambda item: item.value if isinstance(item, ResponseFormat) else "",
)
def test_create_format_returns_report_of_that_format(response_format: ResponseFormat, report_type: type[AbstractReport]):
    """Для каждого формата фабрика возвращает отчёт своего класса."""
    # Подготовка
    factory = ReportFactory(_settings())

    # Действие
    report = factory.create(response_format)

    # Проверка
    assert isinstance(factory, AbstractReportFactory)
    assert type(report) is report_type


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_create_every_format_returns_report(response_format: ResponseFormat):
    """Для каждого формата из ResponseFormat в фабрике есть реализация: новый формат нельзя забыть подключить."""
    # Действие
    report = ReportFactory(_settings()).create(response_format)

    # Проверка
    assert isinstance(report, AbstractReport)


def test_create_returns_new_report_each_time():
    """Каждый вызов create создаёт новый отчёт."""
    # Подготовка
    factory = ReportFactory(_settings())

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
        _ = ReportFactory(_settings()).create(response_format)  # pyright: ignore[reportArgumentType]


def test_create_format_without_report_raises_arguments_exception(monkeypatch: pytest.MonkeyPatch):
    """Для формата, которого нет в сопоставлении фабрики, бросается ArgumentsException."""
    # Подготовка
    monkeypatch.setattr(ReportFactory, "_reports", {})

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportFactory(_settings()).create(ResponseFormat.TXT)


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_create_default_returns_report_of_settings_format(response_format: ResponseFormat):
    """create_default создаёт отчёт того же класса, что create с форматом из настроек."""
    # Подготовка
    factory = ReportFactory(_settings(response_format))

    # Действие
    report = factory.create_default()

    # Проверка
    assert type(report) is type(factory.create(response_format))


def test_create_default_after_settings_change_uses_new_format():
    """Фабрика хранит ссылку на настройки: смена формата в них сразу меняет отчёт по умолчанию."""
    # Подготовка
    settings = _settings(ResponseFormat.TXT)
    factory = ReportFactory(settings)
    settings.response_format = ResponseFormat.XML

    # Действие
    report = factory.create_default()

    # Проверка
    assert type(report) is XmlReport


def test_init_settings_are_stored():
    """Переданные настройки доступны через свойство settings."""
    # Подготовка
    settings = _settings()

    # Действие
    factory = ReportFactory(settings)

    # Проверка
    assert factory.settings is settings


# Подготовка
@pytest.mark.parametrize("settings", [None, "txt", ResponseFormat.TXT])
def test_init_not_settings_raises_arguments_exception(settings: object):
    """Фабрика без настроек не создаётся: create_default не из чего брать формат."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = ReportFactory(settings)  # pyright: ignore[reportArgumentType]
