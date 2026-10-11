import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.nomenclature_catalog import NomenclatureCatalog
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.range_model import RangeModel


def make_nomenclature(name: str) -> NomenclatureModel:
    """Создаёт номенклатуру с корректными данными и заданным наименованием."""
    return NomenclatureModel(
        name,
        f"{name} (полное наименование)",
        NomenclatureGroupModel("Овощи"),
        RangeModel("грамм", 1),
        NomenclatureType.RAW_MATERIAL,
        1,
    )


def test_get_existing_name_returns_same_object():
    """Поиск по наименованию возвращает тот же экземпляр, что передан в справочник, а не копию."""
    # Подготовка
    potato = make_nomenclature("Картофель")
    carrot = make_nomenclature("Морковь")
    catalog = NomenclatureCatalog([potato, carrot])

    # Действие
    result = catalog.get("Морковь")

    # Проверка
    assert result is carrot


def test_get_unknown_name_raises():
    """Если номенклатуры с таким наименованием нет, бросается ArgumentsException."""
    # Подготовка
    catalog = NomenclatureCatalog([make_nomenclature("Картофель")])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        catalog.get("Морковь")


def test_get_name_in_other_case_raises():
    """Наименование ищется точно: другой регистр — другое наименование."""
    # Подготовка
    catalog = NomenclatureCatalog([make_nomenclature("Картофель")])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        catalog.get("картофель")


def test_init_empty_nomenclatures_creates_empty_catalog():
    """Пустой справочник допустим: любой поиск в нём завершается ошибкой."""
    # Подготовка
    catalog = NomenclatureCatalog([])

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        catalog.get("Картофель")


def test_init_duplicate_name_raises():
    """Две номенклатуры с одним наименованием не допускаются: поиск был бы неоднозначным."""
    # Подготовка
    nomenclatures = [make_nomenclature("Картофель"), make_nomenclature("Картофель")]

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NomenclatureCatalog(nomenclatures)


# Подготовка
@pytest.mark.parametrize("value", [None, "Картофель", 1, object()])
def test_init_not_nomenclature_raises(value):
    """Элемент, не являющийся номенклатурой, отвергается."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        NomenclatureCatalog([value])
