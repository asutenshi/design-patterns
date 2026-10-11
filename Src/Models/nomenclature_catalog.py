from collections.abc import Iterable

from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException
from Src.Models.nomenclature_model import NomenclatureModel


class NomenclatureCatalog:
    """Справочник номенклатуры: поиск позиции по наименованию.

    Нужен там, где состав собирается по названиям позиций, например фабричным методам
    технологических карт. Справочник не владеет номенклатурой, а только ссылается на переданные
    объекты: найденная позиция — тот же экземпляр, что лежит в хранилище.

    Наименование ищется точно, как оно записано в номенклатуре. Два элемента с одним
    наименованием в справочник не попадают: поиск был бы неоднозначным.
    """

    # Номенклатура по наименованию
    _items: dict[str, NomenclatureModel]

    def __init__(self, nomenclatures: Iterable[NomenclatureModel]) -> None:
        """Инициализирует справочник.

        :param nomenclatures: Номенклатура справочника.
        :raises ArgumentsException: Если элемент не номенклатура или наименование повторяется.
        """
        self._items = {}
        for nomenclature in nomenclatures:
            nomenclature = CommonValidator.validate_instance(
                nomenclature, NomenclatureModel, "nomenclatures", "Ожидается номенклатура"
            )
            if nomenclature.name in self._items:
                raise ArgumentsException("nomenclatures", f"Номенклатура «{nomenclature.name}» повторяется")

            self._items[nomenclature.name] = nomenclature

    def get(self, name: str) -> NomenclatureModel:
        """Возвращает номенклатуру по наименованию.

        :param name: Искомое наименование.
        :return: Найденная номенклатура.
        :raises ArgumentsException: Если номенклатуры с таким наименованием нет.
        """
        nomenclature = self._items.get(name)
        if nomenclature is None:
            raise ArgumentsException("name", f"Нет номенклатуры «{name}»")
        return nomenclature
