from typing import Self, cast, override

from Src.Core.common_validator import CommonValidator
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

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт группу номенклатуры по полю ``name``.

        :param data: Поля группы.
        :return: Новая группа номенклатуры.
        :raises ArgumentsException: Если наименования нет или оно некорректно.
        """
        return cls(cast(str, CommonValidator.validate_field(data, "name")))

    @staticmethod
    def create_meat() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Мясные продукты»."""
        return NomenclatureGroupModel("Мясные продукты")

    @staticmethod
    def create_dairy() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Молочные продукты»."""
        return NomenclatureGroupModel("Молочные продукты")

    @staticmethod
    def create_vegetables() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Овощи»."""
        return NomenclatureGroupModel("Овощи")

    @staticmethod
    def create_grocery() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Бакалея»."""
        return NomenclatureGroupModel("Бакалея")

    @staticmethod
    def create_semi_finished() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Полуфабрикаты»."""
        return NomenclatureGroupModel("Полуфабрикаты")

    @staticmethod
    def create_dishes() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Блюда»."""
        return NomenclatureGroupModel("Блюда")

    @staticmethod
    def create_packaging() -> "NomenclatureGroupModel":
        """Фабричный метод: создаёт группу «Упаковка»."""
        return NomenclatureGroupModel("Упаковка")