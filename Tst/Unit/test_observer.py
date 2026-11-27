from typing import override

import pytest
from Src.Core.abstract_observer import AbstractObserver
from Src.Core.event_type import EventType
from Src.Core.exception import ArgumentsException
from Src.Core.log_subsystem import LogSubsystem
from Src.Dtos.event_dto import EventDto
from Src.Logics.observer import Observer


class _StubObserver(AbstractObserver):
    """Тестовый подписчик, запоминающий все полученные события."""

    def __init__(self) -> None:
        """Создаёт пустой список полученных событий."""
        self.events: list[EventDto] = []

    @override
    def handle(self, event: EventDto) -> None:
        """Сохраняет поступившее событие."""
        self.events.append(event)


def test_add_duplicate_subscriber_notifies_once():
    """Повторная подписка одного и того же наблюдателя не дублирует доставку событий."""
    # Подготовка
    subscriber = _StubObserver()
    event = EventDto(EventType.ENTITY_CREATED, LogSubsystem.CRUD, "Создана сущность")

    # Действие
    Observer.add(subscriber)
    Observer.add(subscriber)
    Observer.notify(event)

    # Проверка
    assert len(Observer.handlers()) == 1
    assert subscriber.events == [event]


def test_notify_multiple_subscribers_delivers_to_all():
    """Событие доставляется всем подписанным наблюдателям в порядке добавления."""
    # Подготовка
    first = _StubObserver()
    second = _StubObserver()
    event = EventDto(EventType.SETTINGS_CHANGED, LogSubsystem.SETTINGS, "Изменены настройки")
    Observer.add(first)
    Observer.add(second)

    # Действие
    Observer.notify(event)

    # Проверка
    assert first.events == [event]
    assert second.events == [event]


def test_delete_unsubscribes_and_is_idempotent():
    """После отписки наблюдатель больше не получает события, а повторная отписка не падает."""
    # Подготовка
    subscriber = _StubObserver()
    event = EventDto(EventType.WEB_REQUEST, LogSubsystem.WEB, "GET /api/logs")
    Observer.add(subscriber)

    # Действие
    Observer.delete(subscriber)
    Observer.delete(subscriber)
    Observer.notify(event)

    # Проверка
    assert subscriber.events == []
    assert Observer.handlers() == []


def test_notify_subscriber_unsubscribes_during_handle_still_notifies_rest():
    """Если первый подписчик отписывается во время handle, остальные всё равно получают событие."""
    # Подготовка
    class _SelfRemovingObserver(AbstractObserver):
        """Подписчик, отписывающий сам себя при первом событии."""

        @override
        def handle(self, event: EventDto) -> None:
            """Отписывается от Observer при получении события."""
            Observer.delete(self)

    removing = _SelfRemovingObserver()
    second = _StubObserver()
    event = EventDto(EventType.TRANSACTION_ADDED, LogSubsystem.WAREHOUSE, "Приход")
    Observer.add(removing)
    Observer.add(second)

    # Действие
    Observer.notify(event)

    # Проверка
    assert second.events == [event]
    assert Observer.handlers() == [second]


def test_add_non_observer_raises():
    """Подписка объекта, не реализующего AbstractObserver, отклоняется."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Observer.add("not an observer")  # pyright: ignore[reportArgumentType]


def test_notify_non_event_raises():
    """Рассылка объекта, не являющегося EventDto, отклоняется."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Observer.notify("not an event")  # pyright: ignore[reportArgumentType]
