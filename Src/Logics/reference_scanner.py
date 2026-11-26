from collections.abc import Iterable, Mapping
from typing import cast

from Src.Core.abstract_model import AbstractModel
from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator


class ReferenceScanner:
    """Находит прямые ссылки модели на сущности (``BaseEntity``) обходом её графа объектов.

    Правила обхода:

    - Поля модели читаются напрямую из состояния экземпляра (``vars(obj)``), без вызова геттеров:
      вычисляемые свойства не пересчитываются, копии коллекций не создаются, а транзитивные геттеры
      не искажают список прямых ссылок.
    - Встреченная сущность (``BaseEntity``) фиксируется как прямая ссылка, внутрь неё сканер
      не спускается: её собственные ссылки найдёт отдельный вызов ``scan()``. Ссылка на сам
      сканируемый объект (базовая единица ``RangeModel``) пропускается.
    - Вложенные модели без идентификатора (``AbstractModel``, не ``BaseEntity``, например
      ``IngredientModel`` и будущие строки документов) раскрываются рекурсивно: они — часть
      состояния корня, а не самостоятельные сущности.
    - Словари (``Mapping``) обходятся по ключам и значениям, остальные коллекции (``Iterable``,
      включая ``UniqueCollection``, кроме строк, байтов и типов) — поэлементно.
    - Защита от циклов ведётся по тождеству объекта (``id``). Результат не содержит повторов
      по тождеству объекта и сохраняет порядок первого обнаружения: две разные копии сущности
      с одним ``UUID`` не склеиваются, поэтому проверка принадлежности хранилищу видит подмену.
    """

    def scan(self, source: AbstractModel) -> list[BaseEntity]:
        """Возвращает прямые ссылки модели на другие сущности в порядке обхода, без повторов.

        :param source: Сканируемая доменная модель (сущность или вложенная модель).
        :return: Список сущностей, на которые ссылается модель (без самой ``source``).
        :raises ArgumentsException: Если ``source`` не является наследником ``AbstractModel``.
        """
        source = CommonValidator.validate_instance(source, AbstractModel, "source", "Ожидается доменная модель")
        references: list[BaseEntity] = []
        seen_references: set[int] = set()
        visited: set[int] = {id(source)}

        for field_value in self._field_values(source):
            self._walk(field_value, source, visited, seen_references, references)

        return references

    def _walk(
        self,
        value: object,
        root: AbstractModel,
        visited: set[int],
        seen_references: set[int],
        references: list[BaseEntity],
    ) -> None:
        """Рекурсивно обходит значение и собирает найденные ссылки на ``BaseEntity``.

        :param value: Текущее значение поля или элемент контейнера.
        :param root: Исходная модель: ссылки на неё саму пропускаются.
        :param visited: Идентификаторы объектов уже посещённых моделей и контейнеров для защиты от циклов.
        :param seen_references: Идентификаторы объектов уже добавленных ссылок для исключения повторов.
        :param references: Накапливаемый список найденных ссылок.
        """
        if value is None or isinstance(value, (str, bytes, bytearray, type)):
            return

        if isinstance(value, BaseEntity):
            if value is not root:
                ref_id = id(value)
                if ref_id not in seen_references:
                    seen_references.add(ref_id)
                    references.append(value)
            return

        if isinstance(value, AbstractModel):
            obj_id = id(value)
            if obj_id in visited:
                return
            visited.add(obj_id)
            for field_value in self._field_values(value):
                self._walk(field_value, root, visited, seen_references, references)
            return

        if isinstance(value, Mapping):
            mapping = cast(Mapping[object, object], value)
            obj_id = id(mapping)
            if obj_id in visited:
                return
            visited.add(obj_id)
            for key, item in mapping.items():
                self._walk(key, root, visited, seen_references, references)
                self._walk(item, root, visited, seen_references, references)
            return

        if isinstance(value, Iterable):
            obj_id = id(value)
            if obj_id in visited:
                return
            visited.add(obj_id)
            for item in value:
                self._walk(item, root, visited, seen_references, references)

    @staticmethod
    def _field_values(model: AbstractModel) -> Iterable[object]:
        """Возвращает значения всех атрибутов экземпляра модели в порядке их записи.

        :param model: Доменная модель.
        :return: Значения атрибутов экземпляра.
        """
        return cast(dict[str, object], vars(model)).values()
