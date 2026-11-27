from typing import ClassVar

from Src.Core.abstract_observer import AbstractObserver
from Src.Core.common_validator import CommonValidator
from Src.Dtos.event_dto import EventDto


class Observer:
    """Шина событий шаблона «Наблюдатель».

    Хранит список подписчиков ``AbstractObserver`` и рассылает им ``EventDto``,
    не связывая источники событий с конкретными обработчиками.

    Не наследует ``AbstractManager``, потому что шине нечего загружать;
    для изоляции тестов предусмотрен метод ``clear()``.
    """

    # Список активных подписчиков в порядке добавления
    _handlers: ClassVar[list[AbstractObserver]] = []

    @classmethod
    def add(cls, subscriber: AbstractObserver) -> None:
        """Подписывает наблюдателя на события, если он ещё не подписан.

        :param subscriber: Подписчик, реализующий ``AbstractObserver``.
        :raises ArgumentsException: Если передан объект, не являющийся ``AbstractObserver``.
        """
        subscriber = CommonValidator.validate_instance(
            subscriber, AbstractObserver, "subscriber", "Ожидается наблюдатель"
        )
        if subscriber not in cls._handlers:
            cls._handlers.append(subscriber)

    @classmethod
    def delete(cls, subscriber: AbstractObserver) -> None:
        """Отписывает наблюдателя от событий; повторная отписка безопасна.

        :param subscriber: Подписчик для удаления.
        :raises ArgumentsException: Если передан объект, не являющийся ``AbstractObserver``.
        """
        subscriber = CommonValidator.validate_instance(
            subscriber, AbstractObserver, "subscriber", "Ожидается наблюдатель"
        )
        if subscriber in cls._handlers:
            cls._handlers.remove(subscriber)

    @classmethod
    def notify(cls, event: EventDto) -> None:
        """Рассылает событие всем текущим подписчикам.

        :param event: Конверт события.
        :raises ArgumentsException: Если передан объект, не являющийся ``EventDto``.
        """
        event = CommonValidator.validate_instance(event, EventDto, "event", "Ожидается событие")
        for handler in cls.handlers():
            handler.handle(event)

    @classmethod
    def clear(cls) -> None:
        """Удаляет всех подписчиков."""
        cls._handlers.clear()

    @classmethod
    def handlers(cls) -> list[AbstractObserver]:
        """Возвращает копию списка текущих подписчиков."""
        return list(cls._handlers)
