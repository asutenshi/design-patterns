from abc import ABC
from typing import override

import pytest
from Src.Core.exception import ArgumentsException, OperationException, ProjectException


class _TitledException(ProjectException):
    """Минимальный наследник ProjectException для проверки базового поведения."""

    @override
    def _title(self) -> str:
        return "Заголовок"


class _UntitledException(ProjectException, ABC):
    """Наследник без реализации _title: остаётся абстрактным."""


# ---------------------------------------------------------------------------
# ProjectException
# ---------------------------------------------------------------------------


def test_init_project_exception_directly_raises_type_error():
    """Напрямую создать абстрактный ProjectException нельзя."""
    # Действие и проверка
    with pytest.raises(TypeError):
        ProjectException("сообщение")  # pyright: ignore[reportAbstractUsage]


def test_init_subclass_without_title_raises_type_error():
    """Наследник, не реализовавший _title, остаётся абстрактным и не создаётся."""
    # Действие и проверка
    with pytest.raises(TypeError):
        _UntitledException("сообщение")  # pyright: ignore[reportAbstractUsage]


def test_init_subclass_with_title_is_exception():
    """Наследник с реализованным _title создаётся и является Exception."""
    # Действие
    exception = _TitledException("сообщение")

    # Проверка
    assert isinstance(exception, Exception)
    assert isinstance(exception, ProjectException)


def test_str_message_and_stack_trace_follow_title_in_order():
    """Текст ошибки состоит из заголовка, пояснения и трассировки в этом порядке."""
    # Подготовка
    exception = _TitledException("пояснение", "трассировка")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "пояснение", "трассировка"]


def test_str_empty_message_and_stack_trace_contains_only_title():
    """Пустые пояснение и трассировка не добавляют пустых строк."""
    # Подготовка
    exception = _TitledException("")

    # Действие
    text = str(exception)

    # Проверка
    assert text == "Заголовок"


def test_str_empty_stack_trace_has_no_blank_lines():
    """Пустая трассировка не оставляет пустую строку в конце текста."""
    # Подготовка
    exception = _TitledException("пояснение")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "пояснение"]


def test_init_values_with_spaces_are_stripped():
    """Пробелы и переводы строк по краям пояснения и трассировки удаляются."""
    # Подготовка
    exception = _TitledException("  пояснение \n", "\t трассировка  ")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "пояснение", "трассировка"]


def test_init_only_spaces_message_is_treated_as_empty():
    """Пояснение из одних пробелов считается пустым и в текст не попадает."""
    # Подготовка
    exception = _TitledException("   ", "трассировка")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "трассировка"]


def test_init_non_string_message_is_converted_to_string():
    """Нестроковое пояснение приводится к строке."""
    # Подготовка
    exception = _TitledException(404)  # pyright: ignore[reportArgumentType]

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "404"]


def test_init_non_string_stack_trace_is_converted_to_string():
    """Нестроковая трассировка приводится к строке."""
    # Подготовка
    exception = _TitledException("пояснение", 42)  # pyright: ignore[reportArgumentType]

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Заголовок", "пояснение", "42"]


# ---------------------------------------------------------------------------
# ArgumentsException
# ---------------------------------------------------------------------------


def test_str_arguments_exception_all_parts_in_order():
    """Текст ArgumentsException: заголовок с именем аргумента, пояснение, трассировка."""
    # Подготовка
    exception = ArgumentsException("name", "Значение не может быть пустым", "трассировка")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == [
        "Ошибка. Некорректный аргумент name!",
        "Значение не может быть пустым",
        "трассировка",
    ]


def test_str_arguments_exception_only_field_contains_only_title():
    """Без пояснения и трассировки текст ArgumentsException — один заголовок."""
    # Подготовка
    exception = ArgumentsException("name")

    # Действие
    text = str(exception)

    # Проверка
    assert text == "Ошибка. Некорректный аргумент name!"


def test_init_arguments_exception_field_with_spaces_is_stripped():
    """Пробелы по краям имени аргумента удаляются."""
    # Подготовка
    exception = ArgumentsException("  name  ", "пояснение")

    # Действие
    title = str(exception).split("\n")[0]

    # Проверка
    assert title == "Ошибка. Некорректный аргумент name!"


def test_init_arguments_exception_non_string_field_is_converted_to_string():
    """Нестроковое имя аргумента приводится к строке."""
    # Подготовка
    exception = ArgumentsException(123)  # pyright: ignore[reportArgumentType]

    # Действие
    text = str(exception)

    # Проверка
    assert text == "Ошибка. Некорректный аргумент 123!"


def test_init_arguments_exception_is_project_exception():
    """ArgumentsException наследуется от ProjectException."""
    # Действие
    exception = ArgumentsException("name")

    # Проверка
    assert isinstance(exception, ProjectException)


# ---------------------------------------------------------------------------
# OperationException
# ---------------------------------------------------------------------------


def test_str_operation_exception_all_parts_in_order():
    """Текст OperationException: заголовок операции, пояснение, трассировка."""
    # Подготовка
    exception = OperationException("Файл не найден", "трассировка")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Ошибка. Операция не выполнена!", "Файл не найден", "трассировка"]


def test_str_operation_exception_without_stack_trace_has_two_lines():
    """Без трассировки текст OperationException состоит из заголовка и пояснения."""
    # Подготовка
    exception = OperationException("Файл не найден")

    # Действие
    lines = str(exception).split("\n")

    # Проверка
    assert lines == ["Ошибка. Операция не выполнена!", "Файл не найден"]


def test_init_operation_exception_without_message_raises_type_error():
    """Пояснение обязательно: OperationException без аргументов не создаётся."""
    # Действие и проверка
    with pytest.raises(TypeError):
        OperationException()  # pyright: ignore[reportCallIssue]


def test_init_operation_exception_is_project_exception():
    """OperationException наследуется от ProjectException."""
    # Действие
    exception = OperationException("сообщение")

    # Проверка
    assert isinstance(exception, ProjectException)


# ---------------------------------------------------------------------------
# Иерархия и перехват
# ---------------------------------------------------------------------------


def test_except_project_exception_catches_arguments_exception():
    """ArgumentsException ловится через except ProjectException."""
    # Действие и проверка
    with pytest.raises(ProjectException):
        raise ArgumentsException("name", "пояснение")


def test_except_project_exception_catches_operation_exception():
    """OperationException ловится через except ProjectException."""
    # Действие и проверка
    with pytest.raises(ProjectException):
        raise OperationException("пояснение")


# Подготовка
@pytest.mark.parametrize(
    ("exception_type", "other_type"),
    [
        (OperationException, ArgumentsException),
        (ArgumentsException, OperationException),
    ],
)
def test_issubclass_sibling_exceptions_are_unrelated(exception_type, other_type):
    """Исключения-соседи не наследуются друг от друга: ошибка операции не ловится как ошибка аргумента и наоборот."""
    # Действие
    result = issubclass(exception_type, other_type)

    # Проверка
    assert result is False


def test_raise_operation_exception_from_cause_keeps_original_exception():
    """При raise ... from исходная ошибка сохраняется в __cause__."""
    # Подготовка
    cause = FileNotFoundError("settings.json")

    # Действие и проверка
    with pytest.raises(OperationException) as exc_info:
        raise OperationException("Файл не найден") from cause
    assert exc_info.value.__cause__ is cause


def test_raise_arguments_exception_text_is_available_via_exc_info():
    """Текст ошибки доступен через str() перехваченного исключения."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        raise ArgumentsException("name", "пояснение")
    assert "name" in str(exc_info.value)
    assert "пояснение" in str(exc_info.value)