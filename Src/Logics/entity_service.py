import uuid
from typing import cast

from Src.Core.abstract_model import AbstractModel
from Src.Core.common_validator import CommonValidator
from Src.Core.entity_type import EntityType
from Src.Core.exception import (
    ArgumentsException,
    OperationException,
    ReferencedEntityException,
)
from Src.Core.named_entity import NamedEntity
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Logics.storage_manager import StorageManager


class EntityService:
    """Сервис доменных сущностей (Service Layer): создание, изменение и удаление по правилам предметной области.

    Сервис решает, можно ли выполнить операцию, а хранилище только хранит и отдаёт сущности: сервис
    обращается к нему через публичные методы (``find``, ``find_referrers``, ``add``, ``remove``, ``replace``).
    Данные приходят словарём в формате выгрузки (``ConverterFactory``): поля модели, вложенные сущности
    хранилища задаются ссылкой ``{"id": ...}``, а ``model_type`` можно не указывать, его задаёт тип сущности.
    Правила:

    - Все ссылки новой сущности должны вести на сущности хранилища (те же объекты), иначе ошибка аргумента.
    - Код (``id``) уникален во всём хранилище, среди сущностей всех типов.
    - Удалить сущность или сменить ей код нельзя, пока на неё ссылаются другие сущности
      (``ReferencedEntityException``). Менять остальные поля можно: ссылающиеся сущности видят изменения,
      потому что сущность меняется на месте (``StorageManager.replace``), а не заменяется.
    - Операция атомарна: все проверки идут до первого изменения коллекций, при ошибке хранилище не меняется.
    - Каскадной пересборки снимков карт полуфабрикатов при правке сущностей пока нет.
    """

    def __init__(self, storage: StorageManager | None = None) -> None:
        """Создаёт сервис поверх хранилища.

        :param storage: Хранилище, с которым работает сервис; None — единственный экземпляр StorageManager.
        """
        self._storage: StorageManager = storage if storage is not None else StorageManager()

    def create(self, entity_type: EntityType, data: dict[str, object]) -> NamedEntity:
        """Создаёт сущность указанного типа из данных и добавляет её в хранилище.

        :param entity_type: Тип создаваемой сущности.
        :param data: Поля сущности в формате выгрузки. Вложенные сущности хранилища — ссылки ``{"id": ...}``.
            Если указан ``id``, он становится кодом сущности, иначе код создаётся автоматически.
        :return: Созданная сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если тип не EntityType, данные некорректны, ссылка ведёт на неизвестную
            сущность, код уже занят или такое наименование (ключ) уже есть в коллекции.
        """
        entity_type = CommonValidator.validate_instance(entity_type, EntityType, "entity_type", "Ожидается тип сущности")
        entity = self._build_entity(entity_type, data, None)
        self._ensure_id_is_free(entity)
        self._storage.add(entity_type, entity)
        return entity

    def put(self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object]) -> NamedEntity:
        """Полностью заменяет поля сущности значениями из данных, сама сущность остаётся тем же объектом.

        Поля, которых нет в данных, не сохраняются (обязательные приводят к ошибке). Если ``id`` в данных нет,
        код сущности не меняется, если он другой — сущность получает новый код, но только когда на неё
        никто не ссылается.

        :param entity_type: Тип сущности.
        :param entity_id: Текущий код сущности.
        :param data: Все поля сущности в формате выгрузки.
        :return: Изменённая сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если аргументы некорректны, сущности нет, данные некорректны, ссылка ведёт
            на неизвестную сущность, новый код или наименование (ключ) уже заняты.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        return self._update(entity_type, entity_id, data, merge=False)

    def patch(self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object]) -> NamedEntity:
        """Изменяет только указанные в данных поля сущности, остальные сохраняются.

        Слияние поверхностное: значение поля заменяется целиком, в том числе вложенный словарь.
        Остальное, как у ``put()``.

        :param entity_type: Тип сущности.
        :param entity_id: Текущий код сущности.
        :param data: Изменяемые поля сущности в формате выгрузки.
        :return: Изменённая сущность, та же, что лежит в хранилище.
        :raises ArgumentsException: Если аргументы некорректны, сущности нет, данные некорректны, ссылка ведёт
            на неизвестную сущность, новый код или наименование (ключ) уже заняты.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        return self._update(entity_type, entity_id, data, merge=True)

    def delete(self, entity_type: EntityType, entity_id: uuid.UUID) -> None:
        """Удаляет сущность из хранилища, если на неё никто не ссылается.

        :param entity_type: Тип сущности.
        :param entity_id: Код сущности.
        :raises ArgumentsException: Если аргументы некорректны или сущности нет.
        :raises ReferencedEntityException: Если на сущность ссылаются другие сущности.
        """
        entity = self._get(entity_type, entity_id)
        self._ensure_not_referenced(entity)
        self._storage.remove(entity_type, entity)

    def _get(self, entity_type: EntityType, entity_id: uuid.UUID) -> NamedEntity:
        """Возвращает сущность по типу и коду: операции требуют, чтобы она существовала.

        :raises ArgumentsException: Если аргументы некорректны или сущности нет.
        """
        entity = self._storage.find(entity_type, entity_id)
        if entity is None:
            raise ArgumentsException("entity_id", f"Сущность {entity_type.value} с кодом {entity_id} не найдена")
        return entity

    def _update(
        self, entity_type: EntityType, entity_id: uuid.UUID, data: dict[str, object], *, merge: bool
    ) -> NamedEntity:
        """Общая часть ``put()`` и ``patch()``: собирает новую сущность из данных и переносит её состояние на месте.

        Новая сущность собирается в стороне, проверки кода идут до изменения, а ключ уникальности
        хранилище проверяет в ``replace()`` тоже до изменения.

        :param merge: True — данные накладываются на текущие поля сущности (patch), False — заменяют их (put).
        :raises ArgumentsException: См. ``put()``.
        :raises ReferencedEntityException: Если меняется код сущности, на которую ссылаются.
        """
        target = self._get(entity_type, entity_id)
        fields = CommonValidator.validate_dict(data, "data")
        if merge:
            current = cast(dict[str, object], ConverterFactory().convert(target))
            fields = {**current, **fields}
        else:
            fields = {"id": str(target.id), **fields}

        # Сама сущность не попадает в известные: иначе вместо новой собралась бы она же
        fresh = self._build_entity(entity_type, fields, target)
        if fresh.id != target.id:
            self._ensure_id_is_free(fresh)
            self._ensure_not_referenced(target)

        self._storage.replace(entity_type, target, fresh)
        return target

    def _build_entity(self, entity_type: EntityType, data: dict[str, object], exclude: NamedEntity | None) -> NamedEntity:
        """Собирает сущность типа ``entity_type`` из данных; ссылки ``{"id": ...}`` ведут на сущности хранилища.

        Хранилище при этом не меняется.

        :param entity_type: Тип сущности, определяет класс модели.
        :param data: Поля сущности в формате выгрузки; ``model_type`` необязателен.
        :param exclude: Сущность, которую нельзя возвращать по её коду (меняемая): None, если такой нет.
        :return: Новая сущность.
        :raises ArgumentsException: Если данные не словарь, ``model_type`` не тот, ссылка ведёт на неизвестную
            сущность, значения не прошли проверку модели или модель ссылается на то, чего нет в хранилище.
        """
        fields = CommonValidator.validate_dict(data, "data")
        model_class = self._storage.entity_class(entity_type)
        expected_type = AbstractModel.type_name(model_class)
        if fields.get(AbstractModel.TYPE_FIELD, expected_type) != expected_type:
            raise ArgumentsException(
                AbstractModel.TYPE_FIELD, f"Для типа {entity_type.value} ожидается модель {expected_type}"
            )
        fields = {**fields, AbstractModel.TYPE_FIELD: expected_type}

        stored = self._storage.all_entities()
        factory = DeserializerFactory()
        try:
            with factory.session([entity for entity in stored if entity is not exclude]):
                entity = factory.deserialize_as(model_class, fields)
        except OperationException as ex:
            # Для десериализатора это ссылка на неизвестный объект, для вызывающего — некорректные данные
            raise ArgumentsException("data", str(ex)) from ex

        stored_ids = {id(item) for item in stored}
        unknown = [str(ref.id) for ref in entity.references() if id(ref) not in stored_ids]
        if unknown:
            raise ArgumentsException("data", f"Ссылки на сущности, которых нет в хранилище: {', '.join(unknown)}")
        return entity

    def _ensure_id_is_free(self, entity: NamedEntity) -> None:
        """Проверяет, что код сущности не занят ни одной сущностью хранилища любого типа.

        Коды должны быть уникальны во всём хранилище: ``find_referrers()`` сопоставляет ссылки по коду.

        :raises ArgumentsException: Если код занят.
        """
        if any(stored.id == entity.id for stored in self._storage.all_entities()):
            raise ArgumentsException("id", f"Код {entity.id} уже занят")

    def _ensure_not_referenced(self, entity: NamedEntity) -> None:
        """Проверяет, что на сущность никто не ссылается.

        :raises ReferencedEntityException: Если на сущность ссылаются; в исключении описаны ссылающиеся сущности.
        """
        referrers = self._storage.find_referrers(entity.id)
        if referrers:
            raise ReferencedEntityException(entity.id, [self._describe(referrer) for referrer in referrers])

    def _describe(self, entity: NamedEntity) -> str:
        """Возвращает описание сущности для текста ошибки: тип, наименование и код."""
        for entity_type in EntityType:
            if any(item is entity for item in self._storage.entities(entity_type)):
                return f"{entity_type.value}: {entity.name} ({entity.id})"
        return f"{entity.name} ({entity.id})"
