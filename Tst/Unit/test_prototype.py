import pytest
from Src.Core.entity_type import EntityType
from Src.Core.exception import ArgumentsException
from Src.Core.filter_type import FilterType
from Src.Core.named_entity import NamedEntity
from Src.Dtos.filter_dto import FilterDto
from Src.Dtos.filter_item_dto import FilterItemDto
from Src.Logics.prototype import Prototype
from Src.Logics.storage_manager import StorageManager


def equals(field_name: str, value: str) -> FilterItemDto:
    """Создаёт условие полного совпадения."""
    return FilterItemDto(field_name, FilterType.EQUALS, value)


def like(field_name: str, value: str) -> FilterItemDto:
    """Создаёт условие вхождения строки."""
    return FilterItemDto(field_name, FilterType.LIKE, value)


def names(prototype: Prototype[NamedEntity]) -> list[str]:
    """Возвращает наименования моделей прототипа в порядке хранения."""
    return [model.name for model in prototype.data]


def test_clone_empty_filter_returns_new_prototype_with_all_models(first_start_storage: StorageManager):
    """Пустой фильтр пропускает все модели, но результатом всё равно становится новый прототип."""
    # Подготовка
    models = first_start_storage.entities(EntityType.NOMENCLATURE)
    prototype = Prototype(models)

    # Действие
    result = prototype.clone(FilterDto([]))

    # Проверка
    assert result is not prototype
    assert result.data == models


def test_clone_equals_name_returns_only_full_match(first_start_storage: StorageManager):
    """EQUALS не находит позиции, в наименовании которых искомая строка лишь встречается."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))

    # Действие
    result = prototype.clone(FilterDto([equals("name", "Говядина")]))

    # Проверка
    assert names(result) == ["Говядина"]


def test_clone_like_name_returns_all_containing_value(first_start_storage: StorageManager):
    """LIKE находит все позиции, в наименовании которых встречается искомая строка."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))

    # Действие
    result = prototype.clone(FilterDto([like("name", "Говядина")]))

    # Проверка
    assert names(result) == ["Говядина", "Говядина (мякоть)", "Говядина отварная"]


def test_clone_equals_unique_code_returns_single_model(first_start_storage: StorageManager):
    """Уникальный код сравнивается в виде строки, потому что в условии значение всегда строковое."""
    # Подготовка
    models = first_start_storage.entities(EntityType.NOMENCLATURE)
    target = models[3]
    prototype = Prototype(models)

    # Действие
    result = prototype.clone(FilterDto([equals("id", str(target.id))]))

    # Проверка
    assert result.data == [target]


# Подготовка
@pytest.mark.parametrize(
    ("entity_type", "field_name", "value", "expected"),
    [
        (EntityType.NOMENCLATURE, "name", "Соль", ["Соль"]),
        (EntityType.NOMENCLATURE_GROUP, "name", "Овощи", ["Овощи"]),
        (EntityType.RANGE, "name", "литр", ["литр"]),
        (EntityType.RECIPE, "name", "Борщ с говядиной", ["Борщ с говядиной"]),
    ],
)
def test_clone_any_domain_model_uses_same_prototype(
    first_start_storage: StorageManager, entity_type: EntityType, field_name: str, value: str, expected: list[str]
):
    """Один и тот же прототип фильтрует номенклатуру, группы, единицы измерения и рецепты."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(entity_type))

    # Действие
    result = prototype.clone(FilterDto([equals(field_name, value)]))

    # Проверка
    assert names(result) == expected


def test_clone_nested_path_filters_by_base_range(first_start_storage: StorageManager):
    """Условие по вложенному пути находит единицы измерения с указанной базовой единицей."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.RANGE))

    # Действие
    result = prototype.clone(FilterDto([equals("base.name", "грамм")]))

    # Проверка
    assert names(result) == ["грамм", "килограмм"]


def test_clone_several_conditions_keeps_models_matching_all(first_start_storage: StorageManager):
    """Модель остаётся в результате, только если выполнены все условия фильтра."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))
    conditions = [like("name", "Говядина"), equals("group.name", "Полуфабрикаты")]

    # Действие
    result = prototype.clone(FilterDto(conditions))

    # Проверка
    assert names(result) == ["Говядина отварная"]


def test_clone_chained_calls_narrow_previous_result(first_start_storage: StorageManager):
    """Клон можно фильтровать дальше: цепочка вызовов даёт тот же результат, что и общий фильтр."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))

    # Действие
    result = prototype.clone(FilterDto([like("name", "Говядина")])).clone(
        FilterDto([equals("group.name", "Полуфабрикаты")])
    )

    # Проверка
    assert names(result) == ["Говядина отварная"]


def test_clone_list_path_matches_when_any_item_matches(first_start_storage: StorageManager):
    """Рецепт подходит, если условию соответствует хотя бы один ингредиент из состава."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.RECIPE))

    # Действие
    result = prototype.clone(FilterDto([equals("items.nomenclature.name", "Картофель")]))

    # Проверка
    assert names(result) == ["Борщ с говядиной"]


def test_clone_list_path_equals_does_not_match_part_of_value(first_start_storage: StorageManager):
    """EQUALS по составу не срабатывает на ингредиенты, где искомая строка только часть наименования."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.RECIPE))

    # Действие
    result = prototype.clone(FilterDto([equals("items.nomenclature.name", "Говядина")]))

    # Проверка
    assert result.data == []


def test_clone_list_path_like_matches_part_of_value(first_start_storage: StorageManager):
    """LIKE по составу находит рецепты, где искомая строка входит в наименование ингредиента."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.RECIPE))

    # Действие
    result = prototype.clone(FilterDto([like("items.nomenclature.name", "Говядина")]))

    # Проверка
    assert names(result) == ["Говядина отварная", "Борщ с говядиной"]


def test_clone_keeps_source_prototype_unchanged(first_start_storage: StorageManager):
    """После клонирования в исходном прототипе остаются все модели."""
    # Подготовка
    models = first_start_storage.entities(EntityType.NOMENCLATURE)
    prototype = Prototype(models)

    # Действие
    _ = prototype.clone(FilterDto([equals("name", "Соль")]))

    # Проверка
    assert prototype.data == models


def test_clone_returns_same_model_objects(first_start_storage: StorageManager):
    """Прототип копирует список, но не модели: в результате лежат те же объекты, что в хранилище."""
    # Подготовка
    models = first_start_storage.entities(EntityType.NOMENCLATURE)
    salt = next(model for model in models if model.name == "Соль")

    # Действие
    result = Prototype(models).clone(FilterDto([equals("name", "Соль")]))

    # Проверка
    assert result.data[0] is salt


def test_clone_private_field_raises(first_start_storage: StorageManager):
    """Условие по приватному полю отклоняется ошибкой аргумента."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        _ = prototype.clone(FilterDto([equals("_range._factor", "1000")]))


def test_clone_equals_enum_field_compares_enum_value(first_start_storage: StorageManager):
    """Перечисление сравнивается по значению, как в выгрузке и в API: «упаковка», а не NomenclatureType.PACKAGING."""
    # Подготовка
    prototype = Prototype(first_start_storage.entities(EntityType.NOMENCLATURE))

    # Действие
    result = prototype.clone(FilterDto([equals("type", "упаковка")]))

    # Проверка
    assert names(result) == ["Стакан", "Контейнер для супа 500 мл"]
