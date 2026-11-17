import inspect
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override


class ProjectException(Exception, ABC):
    """Абстрактная база исключений проекта.

    Хранит пояснение и трассировку, формирует текст ошибки из заголовка,
    пояснения и трассировки. Заголовок задаёт наследник. Значения приводятся
    к строке и очищаются от пробелов по краям. Позволяет ловить любые ошибки
    проекта одним ``except ProjectException``.

    :param message: Пояснение, что именно произошло.
    :param stack_trace: Дополнительная информация о трассировке.
    """

    _stack_trace: str
    _message: str

    def __init__(self, message: str, stack_trace: str = "") -> None:
        """Инициализирует исключение.

        :param message: Пояснение, что именно произошло.
        :param stack_trace: Дополнительная информация о трассировке.
        :raises TypeError: Если у класса остались нереализованные абстрактные методы.
        """
        # BaseException.__new__ не проверяет abstractmethod (это делает object.__new__),
        # поэтому абстрактность проверяется здесь
        if inspect.isabstract(type(self)):
            raise TypeError(f"Нельзя создать абстрактное исключение {type(self).__name__}")
        super().__init__(message)
        self._message = str(message).strip()
        self._stack_trace = str(stack_trace).strip()


    @abstractmethod
    def _title(self) -> str:
        """Возвращает заголовок ошибки, первую строку текста."""

    @override
    def __str__(self) -> str:
        """Возвращает текст ошибки из заголовка, пояснения и трассировки."""
        parts = [self._title(), self._message, self._stack_trace]
        return "\n".join(p for p in parts if p)


class ArgumentsException(ProjectException):
    """Исключение для некорректных аргументов.

    Выбрасывается, когда в метод, конструктор или сеттер передано недопустимое значение.
    Дополнительно к базе хранит имя проблемного аргумента.

    :param field: Имя некорректного аргумента.
    :param message: Пояснение, что именно не так с аргументом.
    :param stack_trace: Дополнительная информация о трассировке.
    """

    _field: str

    def __init__(self, field: str, message: str = "", stack_trace: str = "") -> None:
        """Инициализирует исключение.

        :param field: Имя некорректного аргумента.
        :param message: Пояснение, что именно не так с аргументом.
        :param stack_trace: Дополнительная информация о трассировке.
        """
        super().__init__(message, stack_trace)
        self._field = str(field).strip()

    @override
    def _title(self) -> str:
        """Возвращает заголовок с именем некорректного аргумента."""
        return f"Ошибка. Некорректный аргумент {self._field}!"


class OperationException(ProjectException):
    """Исключение для ошибок выполнения операции.

    Выбрасывается, когда операция не может быть выполнена, хотя аргументы корректны:
    источник данных недоступен или повреждён, объект не в том состоянии
    (например, настройки ещё не загружены). Для некорректных аргументов
    используется ArgumentsException.

    :param message: Пояснение, почему операция не выполнена.
    :param stack_trace: Дополнительная информация о трассировке.
    """

    @override
    def _title(self) -> str:
        """Возвращает заголовок ошибки операции."""
        return "Ошибка. Операция не выполнена!"


class ReferencedEntityException(ProjectException):
    """Исключение для сущности, на которую есть ссылки.

    Выбрасывается, когда сущность нельзя удалить или изменить ей код, потому что на неё ссылаются
    другие сущности (Docs/.homework.md, п. 3). Аргументы корректны, поэтому это не ArgumentsException,
    а отдельная ошибка: вызывающий код отличает её от прочих ошибок операции (в API это конфликт).
    Хранит код сущности и описания ссылающихся сущностей, а пояснение формирует сам.

    Описания ссылающихся сущностей — строки, а не сами сущности: модуль исключений не должен
    зависеть от моделей, которые сами используют исключения. Описание формирует тот, кто бросает
    исключение, например ``"nomenclature: Свёкла"``.

    :param target_id: Код сущности, на которую ссылаются.
    :param referrers: Описания сущностей, которые ссылаются на неё.
    :param stack_trace: Дополнительная информация о трассировке.
    """

    _target_id: uuid.UUID
    _referrers: tuple[str, ...]

    def __init__(self, target_id: uuid.UUID, referrers: Sequence[str], stack_trace: str = "") -> None:
        """Инициализирует исключение.

        :param target_id: Код сущности, на которую ссылаются.
        :param referrers: Описания сущностей, которые ссылаются на неё. Значения приводятся к строке.
        :param stack_trace: Дополнительная информация о трассировке.
        """
        self._target_id = target_id
        self._referrers = tuple(str(referrer).strip() for referrer in referrers)
        message = f"На сущность {target_id} ссылаются: {'; '.join(self._referrers)}"
        super().__init__(message, stack_trace)

    @property
    def target_id(self) -> uuid.UUID:
        """Возвращает код сущности, на которую ссылаются."""
        return self._target_id

    @property
    def referrers(self) -> tuple[str, ...]:
        """Возвращает описания сущностей, которые ссылаются на неё."""
        return self._referrers

    @override
    def _title(self) -> str:
        """Возвращает заголовок ошибки связанной сущности."""
        return "Ошибка. Сущность используется другими сущностями!"
