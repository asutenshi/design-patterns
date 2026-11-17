import uuid
from abc import ABC
from typing import Self, override

from Src.Core.abstract_model import AbstractModel
from Src.Core.exception import ArgumentsException


class BaseEntity(AbstractModel, ABC):
    """Абстрактный базовый класс для идентифицируемых сущностей.

    Хранит только идентификатор и определяет равенство и хэш по нему.
    Сущности без наименования (остатки, записи журнала, документы) наследуются отсюда,
    сущности с наименованием — от NamedEntity. Тип модели и фабричный метод ``from_dict``
    приходят из AbstractModel.
    """

    # Уникальный идентификатор сущности
    _id: uuid.UUID

    def __init__(self) -> None:
        """Инициализирует базовый экземпляр сущности с новым идентификатором."""
        self._id = uuid.uuid4()

    @property
    def id(self) -> uuid.UUID:
        """Возвращает уникальный идентификатор сущности."""
        return self._id

    @id.setter
    def id(self, value: uuid.UUID) -> None:
        """
        Устанавливает уникальный идентификатор сущности.

        :param value: Новый идентификатор сущности.
        :raises ArgumentsException: Если значение не UUID.
        """
        if not isinstance(value, uuid.UUID):
            raise ArgumentsException("value", "Некорректно передан параметр идентификатора")

        self._id = value

    @override
    def __eq__(self, value: object, /) -> bool:
        """Сравнивает сущности по типу и идентификатору."""
        if type(value) is not type(self):
            return NotImplemented
        return self._id == value._id

    @override
    def __hash__(self) -> int:
        """Возвращает хэш сущности на основе её идентификатора."""
        return hash(self._id)

    def replace_state(self, other: Self) -> None:
        """Заменяет состояние сущности состоянием другой сущности того же типа, включая идентификатор.

        Нужен, чтобы изменить сущность на месте: на неё ссылаются другие сущности хранилища (карта хранит
        номенклатуру, номенклатура — группу), и заменой объекта их ссылки устарели бы. Ссылка новой сущности
        на саму себя (базовая единица измерения) переносится как ссылка на эту сущность. Значения полей
        не проверяются: они уже проверены конструктором ``other``.

        :param other: Сущность того же типа, чьё состояние копируется. После копирования не используется.
        :raises ArgumentsException: Если ``other`` другого типа.
        """
        if type(other) is not type(self):
            raise ArgumentsException("other", f"Ожидается {type(self).__name__}: {type(other).__name__}")

        for key, value in vars(other).items():
            vars(self)[key] = self if value is other else value

    def references(self) -> list["BaseEntity"]:
        """Возвращает сущности, на которые ссылается эта сущность.

        Список нужен для проверки целостности: сущность, на которую ссылаются, нельзя удалять или менять
        ей код (Docs/.homework.md, п. 3). Берутся прямые ссылки, транзитивные (группа номенклатуры
        внутри номенклатуры внутри карты) не раскрываются: их вернёт ``references()`` самой ссылки.
        Саму сущность в список не включают, одна сущность может встретиться несколько раз.
        По умолчанию ссылок нет; сущности со ссылками переопределяют метод.

        :return: Сущности, на которые ссылается эта сущность.
        """
        return []

# В будущем я бы добавл repr для удобной отладки
# Также стоило бы реализовать восстановление сущности по ее известному id, но это уже когда появится БД
