from typing import override

from Src.Core.common_validator import CommonValidator
from Src.Core.named_entity import NamedEntity
from Src.Core.nomenclature_type import NomenclatureType
from Src.Models.nomenclature_group_model import NomenclatureGroupModel
from Src.Models.range_model import RangeModel


class NomenclatureModel(NamedEntity):
    """Модель номенклатуры — единицы учёта.

    Помимо наименования и идентификатора из NamedEntity хранит полное наименование,
    группу номенклатуры, единицу измерения, тип позиции и вес базовой единицы в граммах.
    Все поля обязательны: каждый элемент номенклатуры включён в группу (п. 1.1 ТЗ),
    учитывается в единице измерения и относится к одному из типов (сырьё, полуфабрикат и т. д.).

    Вес базовой единицы (``grams_per_base_unit``) — свойство продукта, а не единицы измерения:
    «миллилитр» один, а масло и бульон весят по-разному. Для граммов это 1, для миллилитров —
    плотность, для штук — вес одной штуки. По нему вес позиции в граммах вычисляется из количества
    в базовой единице (``range.base``), например при расчёте брутто и нетто технологической карты.
    Значение по умолчанию намеренно не задано: молчаливая единица исказила бы вес штучных позиций.

    Ограничение в 50 символов действует на обычное наименование (``name``) только у номенклатуры,
    поэтому свойство переопределено здесь, а не в NamedEntity. Полное наименование (``full_name``)
    ограничено 255 символами независимо от ``name``.

    Идентичность и хэш определяются по ``id`` (см. BaseEntity), поэтому номенклатуру можно
    использовать ключом словаря или элементом множества, в том числе после переименования.

    Не реализовано: блокировка удаления номенклатуры, участвующей в учёте (п. 6.2 ТЗ):
    это логика слоя Logics.
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
    # Тип позиции
    _type: NomenclatureType
    # Вес одной базовой единицы в граммах
    _grams_per_base_unit: int | float

    def __init__(
        self,
        name: str,
        full_name: str,
        group: NomenclatureGroupModel,
        range: RangeModel,
        type: NomenclatureType,
        grams_per_base_unit: float,
    ) -> None:
        """Инициализирует номенклатуру.

        :param name: Наименование, не длиннее 50 символов.
        :param full_name: Полное наименование, не длиннее 255 символов.
        :param group: Группа номенклатуры.
        :param range: Единица измерения (базовая или производная).
        :param type: Тип позиции (сырьё, товар, полуфабрикат, блюдо, упаковка).
        :param grams_per_base_unit: Вес одной базовой единицы в граммах, число больше нуля.
        :raises ArgumentsException: Если любой из параметров не соответствует требованиям.
        """
        super().__init__(name)
        self.full_name = full_name
        self.group = group
        self.range = range
        self.type = type
        self.grams_per_base_unit = grams_per_base_unit

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
        self._name = CommonValidator.validate_string(value, "name", self.NAME_MAX_LENGTH)

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
        self._full_name = CommonValidator.validate_string(value, "full_name", self.FULL_NAME_MAX_LENGTH)

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
        self._group = CommonValidator.validate_instance(value, NomenclatureGroupModel, "group", "Ожидается группа номенклатуры")

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
        self._range = CommonValidator.validate_instance(value, RangeModel, "range", "Ожидается единица измерения")

    @property
    def type(self) -> NomenclatureType:
        """Возвращает тип позиции номенклатуры."""
        return self._type

    @type.setter
    def type(self, value: NomenclatureType) -> None:
        """Устанавливает тип позиции номенклатуры.

        :param value: Новый тип позиции.
        :raises ArgumentsException: Если значение не является NomenclatureType.
        """
        self._type = CommonValidator.validate_instance(value, NomenclatureType, "type", "Ожидается тип номенклатуры")

    @property
    def grams_per_base_unit(self) -> int | float:
        """Возвращает вес одной базовой единицы номенклатуры в граммах."""
        return self._grams_per_base_unit

    @grams_per_base_unit.setter
    def grams_per_base_unit(self, value: float) -> None:
        """Устанавливает вес одной базовой единицы номенклатуры в граммах.

        :param value: Новый вес в граммах, конечное число больше нуля.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное или не больше нуля.
        """
        self._grams_per_base_unit = CommonValidator.validate_positive_number(value, "grams_per_base_unit")