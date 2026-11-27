from datetime import datetime
from typing import Self, cast, override

from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.log_level import LogLevel
from Src.Core.log_subsystem import LogSubsystem


class LogModel(BaseEntity):
    """Модель записи журнала логирования.

    Проектные решения:

    - Наименования у записи нет, поэтому модель наследует ``BaseEntity``, как ``TransactionModel``:
      получает идентификатор, ``model_type`` и ``from_dict`` для сериализации и будущего хранения в SQLite.
    - Все поля задаются только в конструкторе и не имеют сеттеров: уже записанный лог менять нельзя.
    - Публичные свойства позволяют без правок передавать записи в ``Prototype``, ``Sorter`` и ``ConverterFactory``.
    """

    # Дата и время события
    _period: datetime
    # Подсистема, в которой произошло событие
    _subsystem: LogSubsystem
    # Уровень важности сообщения
    _level: LogLevel
    # Текст сообщения
    _message: str

    def __init__(
        self,
        period: datetime,
        subsystem: LogSubsystem,
        level: LogLevel,
        message: str,
    ) -> None:
        """Инициализирует запись лога.

        :param period: Дата и время события.
        :param subsystem: Подсистема, породившая запись.
        :param level: Уровень важности сообщения.
        :param message: Непустой текст сообщения.
        :raises ArgumentsException: Если любой из параметров имеет неверный тип или сообщение пусто.
        """
        super().__init__()
        self._period = CommonValidator.validate_instance(period, datetime, "period", "Ожидается дата и время")
        self._subsystem = CommonValidator.validate_instance(
            subsystem, LogSubsystem, "subsystem", "Ожидается подсистема логирования"
        )
        self._level = CommonValidator.validate_instance(level, LogLevel, "level", "Ожидается уровень логирования")
        self._message = CommonValidator.validate_string(message, "message")

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт запись лога по полям ``period``, ``subsystem``, ``level`` и ``message``.

        Дата записана в JSON строкой ISO 8601, подсистема и уровень — значениями перечислений.

        :param data: Поля записи лога.
        :return: Новая запись лога.
        :raises ArgumentsException: Если обязательного поля нет или значение не проходит проверку.
        """
        return cls(
            period=CommonValidator.validate_datetime(CommonValidator.validate_field(data, "period"), "period"),
            subsystem=CommonValidator.validate_enum(
                CommonValidator.validate_field(data, "subsystem"), LogSubsystem, "subsystem"
            ),
            level=CommonValidator.validate_enum(CommonValidator.validate_field(data, "level"), LogLevel, "level"),
            message=cast(str, CommonValidator.validate_field(data, "message")),
        )

    @property
    def period(self) -> datetime:
        """Возвращает дату и время события."""
        return self._period

    @property
    def subsystem(self) -> LogSubsystem:
        """Возвращает подсистему, породившую запись."""
        return self._subsystem

    @property
    def level(self) -> LogLevel:
        """Возвращает уровень важности сообщения."""
        return self._level

    @property
    def message(self) -> str:
        """Возвращает текст сообщения."""
        return self._message
