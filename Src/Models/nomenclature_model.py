from typing import override

from Src.Core.base_entity import BaseEntity
from Src.Core.validator import Validator
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.range_model import RangeModel


class NomenclatureModel(BaseEntity):
    """Модель номенклатуры — единицы учёта.

    Помимо наименования и идентификатора из BaseEntity хранит полное наименование,
    группу номенклатуры и единицу измерения. Группа и единица обязательны:
    каждый элемент номенклатуры включён в группу (п. 1.1 ТЗ) и учитывается в единице измерения.

    Ограничение в 50 символов действует на обычное наименование (``name``) только у номенклатуры,
    поэтому свойство переопределено здесь, а не в BaseEntity. Полное наименование (``full_name``)
    ограничено 255 символами независимо от ``name``.

    Идентичность и хэш определяются по ``id`` (см. BaseEntity), поэтому номенклатуру можно
    использовать ключом словаря или элементом множества, в том числе после переименования.

    Не реализовано:

    - тип позиции (сырьё, товар, полуфабрикат, блюдо, упаковка) из Docs/DomainEntities.md:
      в текущем задании его нет; появится отдельным полем и перечислением;
    - блокировка удаления номенклатуры, участвующей в учёте (п. 6.2 ТЗ): это логика слоя Logics.
    """

    # Максимальная длина обычного наименования
    NAME_MAX_LENGTH: int = 50
    # Максимальная длина полного наименования
    FULL_NAME_MAX_LENGTH: int = 255

    # Наименование (объявлено из-за переопределения свойства name с ограничением длины)
    _name: str
    # Полное наименование
    _full_name: str
    # Группа номенклатуры
    _group: NomenclatureGroupModel
    # Единица измерения
    _range: RangeModel

    def __init__(self, name: str, full_name: str, group: NomenclatureGroupModel, range: RangeModel) -> None:
        """Инициализирует номенклатуру.

        :param name: Наименование, не длиннее 50 символов.
        :param full_name: Полное наименование, не длиннее 255 символов.
        :param group: Группа номенклатуры.
        :param range: Единица измерения (базовая или производная).
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям.
        """
        super().__init__(name)
        self.full_name = full_name
        self.group = group
        self.range = range

    @property
    @override
    def name(self) -> str:
        """Возвращает наименование номенклатуры."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Устанавливает наименование номенклатуры.

        :param value: Новое наименование.
        :raises ArgumentsException: Если значение не строка, пустое, состоит из пробелов
            или длиннее NAME_MAX_LENGTH символов.
        """
        self._name = Validator.validate_string(value, "name", self.NAME_MAX_LENGTH)

    @property
    def full_name(self) -> str:
        """Возвращает полное наименование номенклатуры."""
        return self._full_name

    @full_name.setter
    def full_name(self, value: str) -> None:
        """Устанавливает полное наименование номенклатуры.

        :param value: Новое полное наименование.
        :raises ArgumentsException: Если значение не строка, пустое, состоит из пробелов
            или длиннее FULL_NAME_MAX_LENGTH символов.
        """
        self._full_name = Validator.validate_string(value, "full_name", self.FULL_NAME_MAX_LENGTH)

    @property
    def group(self) -> NomenclatureGroupModel:
        """Возвращает группу номенклатуры."""
        return self._group

    @group.setter
    def group(self, value: NomenclatureGroupModel) -> None:
        """Устанавливает группу номенклатуры.

        :param value: Новая группа.
        :raises ArgumentsException: Если значение не является NomenclatureGroupModel.
        """
        self._group = Validator.validate_instance(value, NomenclatureGroupModel, "group", "Ожидается группа номенклатуры")

    @property
    def range(self) -> RangeModel:
        """Возвращает единицу измерения номенклатуры."""
        return self._range

    @range.setter
    def range(self, value: RangeModel) -> None:
        """Устанавливает единицу измерения номенклатуры.

        :param value: Новая единица измерения.
        :raises ArgumentsException: Если значение не является RangeModel.
        """
        self._range = Validator.validate_instance(value, RangeModel, "range", "Ожидается единица измерения")