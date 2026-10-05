import inspect
from abc import ABC, abstractmethod
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
