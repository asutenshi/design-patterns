from datetime import datetime

from Src.Core.common_validator import CommonValidator
from Src.Core.event_type import EventType
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem


class EventDto:
    """Конверт события для шаблона «Наблюдатель».

    Содержит общие метаданные события и необязательный ``payload`` с доменным объектом
    для специализированных подписчиков.
    """

    # Тип произошедшего события
    _event_type: EventType
    # Подсистема-источник события
    _subsystem: LogSubsystem
    # Уровень важности события
    _level: LogLevel
    # Человекочитаемое описание события
    _message: str
    # Дата и время события
    _period: datetime
    # Полезная нагрузка события
    _payload: object | None

    def __init__(
        self,
        event_type: EventType,
        subsystem: LogSubsystem,
        message: str,
        level: LogLevel = LogLevel.INFO,
        period: datetime | None = None,
        payload: object | None = None,
    ) -> None:
        """Инициализирует конверт события.

        :param event_type: Тип события.
        :param subsystem: Подсистема, в которой произошло событие.
        :param message: Непустое описание события.
        :param level: Уровень важности, по умолчанию ``LogLevel.INFO``.
        :param period: Дата и время события; ``None`` — текущее местное время.
        :param payload: Произвольная полезная нагрузка для специализированных подписчиков.
        :raises ArgumentsException: Если обязательные поля имеют неверный тип или сообщение пусто.
        """
        self._event_type = CommonValidator.validate_instance(
            event_type, EventType, "event_type", "Ожидается тип события"
        )
        self._subsystem = CommonValidator.validate_instance(
            subsystem, LogSubsystem, "subsystem", "Ожидается подсистема логирования"
        )
        self._message = CommonValidator.validate_string(message, "message")
        self._level = CommonValidator.validate_instance(level, LogLevel, "level", "Ожидается уровень логирования")
        self._period = (
            datetime.now()
            if period is None
            else CommonValidator.validate_instance(period, datetime, "period", "Ожидается дата и время")
        )
        self._payload = payload

    @property
    def event_type(self) -> EventType:
        """Возвращает тип события."""
        return self._event_type

    @property
    def subsystem(self) -> LogSubsystem:
        """Возвращает подсистему-источник события."""
        return self._subsystem

    @property
    def level(self) -> LogLevel:
        """Возвращает уровень важности события."""
        return self._level

    @property
    def message(self) -> str:
        """Возвращает описание события."""
        return self._message

    @property
    def period(self) -> datetime:
        """Возвращает дату и время события."""
        return self._period

    @property
    def payload(self) -> object | None:
        """Возвращает полезную нагрузку события или None."""
        return self._payload
