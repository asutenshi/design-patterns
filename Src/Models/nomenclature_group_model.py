from Src.Core.named_entity import NamedEntity


class NomenclatureGroupModel(NamedEntity):
    """Модель группы номенклатуры — классификатор номенклатурных позиций.

    Собственных полей нет: ТЗ требует только наименование и идентификатор,
    которые приходят из NamedEntity. Ограничения на длину наименования нет.
    Связь «номенклатура → группа» (N–1) хранится на стороне NomenclatureModel.
    """

    def __init__(self, name: str) -> None:
        """Инициализирует группу номенклатуры.

        :param name: Наименование группы.
        :raises ArgumentsException: Если наименование не строка, пустое или состоит из пробелов.
        """
        super().__init__(name)