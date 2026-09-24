class ArgumentsException(Exception):
    """Исключение для некорректных аргументов.

    Выбрасывается, когда в метод, конструктор или сеттер передано недопустимое значение.
    Хранит имя проблемного аргумента, пояснение и, при необходимости, трассировку.
    Значения приводятся к строке и очищаются от пробелов по краям.

    :param field: Имя некорректного аргумента.
    :param message: Пояснение, что именно не так с аргументом.
    :param stack_trace: Дополнительная информация о трассировке.
    """

    _stack_trace: str
    _message: str
    _field: str

    def __init__(self, field: str, message: str = "", stack_trace: str = "") -> None:
        """Инициализирует исключение.

        :param field: Имя некорректного аргумента.
        :param message: Пояснение, что именно не так с аргументом.
        :param stack_trace: Дополнительная информация о трассировке.
        """
        self._field = str(field).strip()
        self._message = str(message).strip()
        self._stack_trace = str(stack_trace).strip()

    def __str__(self) -> str:
        """Возвращает текст ошибки из имени аргумента, пояснения и трассировки."""
        parts = [f"Ошибка. Некорректный аргумент {self._field}!", self._message, self._stack_trace]
        return "\n".join(p for p in parts if p)