import pytest
from Src.Core.abstract_report import AbstractReport
from Src.Core.exception import ArgumentsException
from Src.Core.ownership_form import OwnershipForm
from Src.Core.response_format import ResponseFormat
from Src.Logics.report_factory import ReportFactory
from Src.Logics.storage_manager import StorageManager
from Src.Models.organization_model import OrganizationModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.settings_model import SettingsModel

# Проверки одного состава данных во всех форматах. Разметка каждого формата проверяется
# в его собственном файле тестов: test_txt_report, test_markdown_report и т. д.

_format_scalar = AbstractReport._format_scalar  # pyright: ignore[reportPrivateUsage]


def _report(response_format: ResponseFormat) -> AbstractReport:
    """Создаёт отчёт формата через фабрику, как это делает API."""
    organization = OrganizationModel("Ромашка", "1234567894", "123456789", "12345678901234567890", OwnershipForm.LLC)
    return ReportFactory(SettingsModel(organization, "Иванов И. И.", "Петрова А. А.")).create(response_format)


def _find_recipe(storage: StorageManager, name: str) -> RecipeModel:
    """Возвращает карту из хранилища по наименованию, падает, если её нет."""
    recipe = storage.find_recipe_by_name(name)
    assert recipe is not None
    return recipe


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_build_range_every_format_contains_all_fields_and_values(
    first_start_storage: StorageManager, response_format: ResponseFormat
):
    """В отчёте по единице измерения любого формата есть имя и значение каждого её поля."""
    # Подготовка
    kilogram = next(item for item in first_start_storage.ranges if item.name == "килограмм")

    # Действие
    text = _report(response_format).build(kilogram).text

    # Проверка
    for field in ("id", "name", "base", "factor", "is_base"):
        assert field in text
    for value in (str(kilogram.id), "килограмм", "грамм", str(kilogram.base.id), "1000", "False"):
        assert value in text


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_build_nomenclature_every_format_contains_references_and_type(
    first_start_storage: StorageManager, response_format: ResponseFormat
):
    """Номенклатура в любом формате содержит ссылки на группу и единицу (наименование и код) и тип."""
    # Подготовка
    beet = next(item for item in first_start_storage.nomenclatures if item.name == "Свёкла")

    # Действие
    text = _report(response_format).build(beet).text

    # Проверка
    for value in (
        "Свёкла столовая свежая",
        beet.group.name,
        str(beet.group.id),
        beet.range.name,
        str(beet.range.id),
        "сырьё",
    ):
        assert value in text


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_build_recipe_every_format_contains_steps_items_and_weights(
    first_start_storage: StorageManager, response_format: ResponseFormat
):
    """Отчёт по борщу в любом формате содержит все шаги, все ингредиенты, состав полуфабрикатов и итоговые веса."""
    # Подготовка
    borscht = _find_recipe(first_start_storage, "Борщ с говядиной")
    nested = [part for item in borscht.items for part in item.base]

    # Действие
    text = _report(response_format).build(borscht).text

    # Проверка
    assert nested, "в борще должны быть полуфабрикаты с основанием"
    for step in borscht.steps:
        assert step in text
    for item in [*borscht.items, *nested]:
        assert item.nomenclature.name in text
        assert str(item.nomenclature.id) in text
    assert _format_scalar(borscht.gross_weight) in text
    assert _format_scalar(borscht.net_weight) in text


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
def test_build_same_source_twice_every_format_returns_equal_results(
    first_start_storage: StorageManager, response_format: ResponseFormat
):
    """Два отчёта одного формата по одной сущности равны: результат сравнивается по содержимому."""
    # Подготовка
    recipe = _find_recipe(first_start_storage, "Борщ с говядиной")
    report = _report(response_format)

    # Действие
    first = report.build(recipe)
    second = report.build(recipe)

    # Проверка
    assert first == second
    assert first is not second


# Подготовка
@pytest.mark.parametrize("response_format", list(ResponseFormat), ids=lambda item: item.value)
@pytest.mark.parametrize("source", [None, "карта", object()], ids=["none", "str", "object"])
def test_build_not_named_entity_every_format_raises_arguments_exception(
    response_format: ResponseFormat, source: object
):
    """Источник, не являющийся сущностью с наименованием, отвергается любым форматом."""
    # Подготовка
    report = _report(response_format)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = report.build(source)  # pyright: ignore[reportArgumentType]
