from pathlib import Path
from typing import ClassVar, Self, cast, override

from Src.Core.abstract_manager import AbstractManager
from Src.Core.abstract_observer import AbstractObserver
from Src.Core.common_validator import CommonValidator
from Src.Dtos.event_dto import EventDto
from Src.Logics.observer import Observer
from Src.Models.log_model import LogModel


class LoggerManager(AbstractManager, AbstractObserver):
    """Менеджер логирования.

    Подписывается на ``Observer``, преобразует входящие ``EventDto`` в неизменяемые ``LogModel``
    и хранит их в памяти в порядке поступления. При необходимости сохраняет текст выгрузки в файл.
    """

    # Единственный экземпляр менеджера
    _instance: ClassVar["LoggerManager | None"] = None

    # Накопленные записи лога в порядке поступления
    _logs: list[LogModel]

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса, при первом обращении создаёт его."""
        instance = cast(Self | None, cls.__dict__.get("_instance"))
        if instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            cls._instance = instance
        return instance

    @override
    def _initialize(self) -> None:
        """Инициализирует пустой журнал логов."""
        super()._initialize()
        self._logs = []

    @override
    def load(self) -> None:
        """Активирует менеджер: подписывает его на ``Observer`` и отмечает загруженным.

        Подписка вынесена в ``load()``, а не в ``_initialize()``: хук не должен создавать побочные
        связи с другими компонентами.
        """
        self._is_loaded = False
        Observer.add(self)
        self._is_loaded = True

    @override
    def handle(self, event: EventDto) -> None:
        """Превращает поступившее событие в запись ``LogModel`` и сохраняет её в журнал.

        :param event: Событие, полученное от ``Observer``.
        :raises ArgumentsException: Если передан не ``EventDto``.
        """
        event = CommonValidator.validate_instance(event, EventDto, "event", "Ожидается событие")
        log = LogModel(
            period=event.period,
            subsystem=event.subsystem,
            level=event.level,
            message=event.message,
        )
        self._logs.append(log)

    @property
    def logs(self) -> list[LogModel]:
        """Возвращает копию списка записей лога в порядке поступления."""
        return list(self._logs)

    def clear(self) -> None:
        """Очищает накопленные в памяти записи лога."""
        self._logs.clear()

    def save(self, file_name: str, content: str) -> Path:
        """Сохраняет подготовленный текст лога в файл UTF-8.

        :param file_name: Путь к файлу.
        :param content: Текст для записи.
        :return: Путь к сохранённому файлу.
        :raises ArgumentsException: Если путь пуст или содержимое не строка.
        """
        cleaned_path = CommonValidator.validate_string(file_name, "file_name")
        text = CommonValidator.validate_instance(content, str, "content", "Ожидается строка")
        path = Path(cleaned_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
        return path
