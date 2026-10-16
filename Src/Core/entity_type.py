from enum import Enum


class EntityType(Enum):
    """Тип сущности, которую можно найти в хранилище по коду.

    Значения — строки: в таком виде тип задаётся в параметре запроса API.
    """

    # Номенклатура
    NOMENCLATURE = "nomenclature"
    # Единица измерения
    RANGE = "range"
    # Технологическая карта
    RECIPE = "recipe"
