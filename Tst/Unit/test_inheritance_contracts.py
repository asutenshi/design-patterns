import inspect

import pytest
from Src.Core.abstract_file_manager import AbstractFileManager
from Src.Core.abstract_manager import AbstractManager
from Src.Core.base_entity import BaseEntity
from Src.Core.named_entity import NamedEntity
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.nomenclature_model import NomenclatureModel
from Src.Models.organization_model import OrganizationModel
from Src.Models.range_model import RangeModel
from Src.Models.settings_model import SettingsModel
from Src.Models.warehouse_model import WarehouseModel


def _all_subclasses(base: type) -> list[type]:
    """Возвращает все подклассы base на любой глубине наследования."""
    result: list[type] = []
    for subclass in base.__subclasses__():
        result.append(subclass)
        result.extend(_all_subclasses(subclass))
    return result


def _project_subclasses(base: type) -> list[type]:
    """Возвращает подклассы base из кода проекта, без тестовых заглушек."""
    return [cls for cls in _all_subclasses(base) if cls.__module__.startswith("Src.")]


def _concrete_subclasses(base: type) -> list[type]:
    """Возвращает неабстрактные подклассы base из кода проекта."""
    return [cls for cls in _project_subclasses(base) if not inspect.isabstract(cls)]


# ---------------------------------------------------------------------------
# AbstractManager и AbstractFileManager: наследники не меняют общий порядок работы
#
# Тесты load() для файловых менеджеров написаны один раз для AbstractFileManager
# (test_abstract_file_manager). Они распространяются на наследников, пока те не
# переопределяют load(). Singleton базовые классы не реализуют: его делает каждый
# конкретный менеджер в своём __new__, и здесь это проверяется автоматически.
# ---------------------------------------------------------------------------


def test_managers_project_subclasses_are_discovered():
    """Поиск подклассов находит реальные менеджеры, иначе проверки ниже ничего не проверяют."""
    # Действие
    managers = _project_subclasses(AbstractManager)
    file_managers = _project_subclasses(AbstractFileManager)

    # Проверка
    assert AbstractFileManager in managers
    assert SettingsManager in managers
    assert StorageManager in managers
    assert SettingsManager in file_managers


def test_managers_storage_manager_is_not_file_manager():
    """StorageManager не читает файлы, поэтому не наследует файловую базу (принцип Лисков)."""
    # Действие и проверка
    assert not issubclass(StorageManager, AbstractFileManager)


# Подготовка
@pytest.mark.parametrize("manager_type", _concrete_subclasses(AbstractManager), ids=lambda cls: cls.__name__)
def test_managers_concrete_class_defines_own_singleton(manager_type: type):
    """Конкретный менеджер сам реализует Singleton: у него свои __new__ и _instance."""
    # Действие
    missing = {"__new__", "_instance"} - set(vars(manager_type))

    # Проверка
    assert missing == set()


# Подготовка
@pytest.mark.parametrize("manager_type", _concrete_subclasses(AbstractManager), ids=lambda cls: cls.__name__)
def test_managers_same_class_returns_same_instance(manager_type: type):
    """Повторное создание одного класса возвращает тот же экземпляр."""
    # Действие
    first = manager_type()
    second = manager_type()

    # Проверка
    assert first is second


def test_managers_different_classes_return_different_instances():
    """Разные менеджеры получают разные экземпляры."""
    # Действие и проверка
    assert SettingsManager() is not StorageManager()


def test_managers_subclass_of_manager_returns_own_instance():
    """Наследник конкретного менеджера не получает экземпляр родителя."""

    class _ChildSettingsManager(SettingsManager):
        pass

    # Подготовка
    parent = SettingsManager()

    # Действие
    child = _ChildSettingsManager()

    # Проверка
    assert child is not parent
    assert type(child) is _ChildSettingsManager


# Подготовка
@pytest.mark.parametrize("manager_type", _project_subclasses(AbstractFileManager), ids=lambda cls: cls.__name__)
def test_file_managers_subclass_does_not_override_load(manager_type: type):
    """Файловый менеджер не переопределяет load(): порядок загрузки задаёт AbstractFileManager."""
    # Действие
    overrides_load = "load" in vars(manager_type)

    # Проверка
    assert overrides_load is False


# ---------------------------------------------------------------------------
# BaseEntity и NamedEntity: наследники не меняют идентичность и наименование
#
# Тесты id, равенства и хэша написаны один раз для BaseEntity (test_entities),
# тесты наименования — для NamedEntity (test_named_entity). Модели их не повторяют,
# пока не переопределяют эти члены. Исключение — модели с собственными правилами,
# они перечислены явно и тестируют переопределённое сами.
# ---------------------------------------------------------------------------

# Модели, которые намеренно переопределяют name (своё ограничение длины)
_NAME_OVERRIDING_MODELS: set[type] = {NomenclatureModel}


def test_entities_project_subclasses_are_discovered():
    """Поиск подклассов находит все модели, иначе проверки ниже ничего не проверяют."""
    # Действие
    base_entities = _project_subclasses(BaseEntity)
    named_entities = _project_subclasses(NamedEntity)

    # Проверка
    for model in (WarehouseModel, NomenclatureGroupModel, RangeModel, NomenclatureModel, OrganizationModel):
        assert model in named_entities
    assert SettingsModel in base_entities
    assert SettingsModel not in named_entities


# Подготовка
@pytest.mark.parametrize("entity_type", _project_subclasses(BaseEntity), ids=lambda cls: cls.__name__)
def test_entities_subclass_does_not_override_identity(entity_type: type):
    """Модель не переопределяет id, __eq__ и __hash__: идентичность задаёт BaseEntity."""
    # Действие
    overridden = {"id", "__eq__", "__hash__"} & set(vars(entity_type))

    # Проверка
    assert overridden == set()


# Подготовка
@pytest.mark.parametrize("entity_type", _project_subclasses(NamedEntity), ids=lambda cls: cls.__name__)
def test_named_entities_subclass_overrides_name_only_when_listed(entity_type: type):
    """Свойство name переопределяют только модели из списка исключений, у остальных его проверяет NamedEntity."""
    # Действие
    overrides_name = "name" in vars(entity_type)

    # Проверка
    assert overrides_name == (entity_type in _NAME_OVERRIDING_MODELS)
