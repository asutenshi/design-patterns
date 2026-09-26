from Src.Core.base_entity import BaseEntity


class WarehouseModel(BaseEntity):
    """Модель склада — места хранения остатков.

    Собственных полей нет: ТЗ требует только наименование и идентификатор,
    которые приходят из BaseEntity. Ограничения на длину наименования нет.
    Связь «склад → помещение» (N–1) из Docs/DomainEntities.md пока не реализована,
    так как модель помещения в текущем ТЗ не запрашивалась.
    """

    def __init__(self, name: str) -> None:
        """Инициализирует склад.

        :param name: Наименование склада.
        :raises ArgumentsException: Если наименование не строка, пустое или состоит из пробелов.
        """
        super().__init__(name)