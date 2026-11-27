from abc import ABC, abstractmethod

from Src.Dtos.event_dto import EventDto


class AbstractObserver(ABC):
    """Абстрактный наблюдатель в шаблоне «Наблюдатель».

    Любой класс, который получает события от ``Observer``, реализует этот контракт.
    """

    @abstractmethod
    def handle(self, event: EventDto) -> None:
        """Обрабатывает поступившее событие.

        :param event: Конверт события с метаданными и полезной нагрузкой.
        """
