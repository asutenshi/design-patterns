from enum import Enum


class EntityType(Enum):
    """Тип сущности, которую можно найти в хранилище по коду.

    Значения — строки: в таком виде тип задаётся в параметре запроса API.
    """

    # Номенклатура
    NOMENCLATURE = "nomenclature"
    # Группа номенклатуры
    NOMENCLATURE_GROUP = "nomenclature_group"
    # Единица измерения
    RANGE = "range"
    # Склад
    WAREHOUSE = "warehouse"
    # Технологическая карта
    RECIPE = "recipe"
