from typing import Self, override

import pytest
from Src.Core.abstract_model import AbstractModel
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Core.named_entity import NamedEntity
from Src.Models.ingredient_model import IngredientModel
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.organization_model import OrganizationModel
from Src.Models.range_model import RangeModel
from Src.Models.recipe_model import RecipeModel
from Src.Models.settings_model import SettingsModel
from Src.Models.warehouse_model import WarehouseModel

# Все конкретные модели проекта
_MODELS = [
    RangeModel,
    NomenclatureGroupModel,
    NomenclatureModel,
    WarehouseModel,
    IngredientModel,
    RecipeModel,
    OrganizationModel,
    SettingsModel,
]


class ModelStub(AbstractModel):
    """Модель-заглушка, объявленная вне Src: попадает в реестр так же, как модели проекта."""

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Создаёт модель без полей."""
        return cls()


def test_model_type_range_returns_module_and_class_name():
    """Тип модели — полное имя класса: модуль и имя класса."""
    # Подготовка
    gram = RangeModel("грамм", 1)

    # Действие
    result = gram.model_type

    # Проверка
    assert result == "Src.Models.range_model.RangeModel"


def test_model_type_type_field_matches_property_name():
    """Имя поля типа в JSON совпадает с именем свойства: так ConverterFactory записывает его сам."""
    # Действие и проверка
    assert isinstance(getattr(AbstractModel, AbstractModel.TYPE_FIELD), property)


def test_model_type_entity_and_ingredient_share_root():
    """И сущности, и строка состава карты (без id) — наследники AbstractModel."""
    # Действие и проверка
    assert issubclass(BaseEntity, AbstractModel)
    assert issubclass(IngredientModel, AbstractModel)
    assert not issubclass(IngredientModel, BaseEntity)


# Подготовка
@pytest.mark.parametrize("model_class", _MODELS, ids=lambda cls: cls.__name__)
def test_resolve_type_project_model_returns_its_class(model_class: type[AbstractModel]):
    """Каждая конкретная модель проекта находится в реестре по своему типу."""
    # Подготовка
    model_type = f"{model_class.__module__}.{model_class.__qualname__}"

    # Действие
    result = AbstractModel.resolve_type(model_type)

    # Проверка
    assert result is model_class


def test_resolve_type_subclass_declared_later_is_registered():
    """Наследник попадает в реестр при объявлении класса, без ручной регистрации."""
    # Подготовка
    model_type = ModelStub().model_type

    # Действие
    result = AbstractModel.resolve_type(model_type)

    # Проверка
    assert result is ModelStub


# Подготовка
@pytest.mark.parametrize(
    "model_class", [AbstractModel, BaseEntity, NamedEntity], ids=lambda cls: cls.__name__
)
def test_resolve_type_abstract_class_raises(model_class: type):
    """Абстрактный класс по типу не находится: собрать его нельзя."""
    # Подготовка
    model_type = f"{model_class.__module__}.{model_class.__qualname__}"

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        AbstractModel.resolve_type(model_type)


# Подготовка
@pytest.mark.parametrize(
    "model_type",
    ["Src.Models.missing_model.MissingModel", "os.system", "RangeModel", ""],
    ids=["missing", "not_model", "short_name", "empty"],
)
def test_resolve_type_unknown_type_raises(model_type: str):
    """Тип, которого нет в реестре, — ArgumentsException: модуль по строке из файла не импортируется."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        AbstractModel.resolve_type(model_type)
    assert "model_type" in str(exc_info.value)


# Подготовка
@pytest.mark.parametrize("model_type", [None, 1, RangeModel], ids=["none", "int", "class"])
def test_resolve_type_not_a_string_raises(model_type: object):
    """Тип модели не строка — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        AbstractModel.resolve_type(model_type)
