import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.validator import Validator


class ParentStub:
    """Родительский класс-заглушка для проверки validate_instance."""


class ChildStub(ParentStub):
    """Дочерний класс-заглушка для проверки validate_instance."""


def test_validate_string_valid_value_returned():
    """Корректная строка возвращается без изменений."""
    # Подготовка
    value = "Мука"

    # Действие
    result = Validator.validate_string(value, "name")

    # Проверка
    assert result == "Мука"


def test_validate_string_surrounding_spaces_stripped():
    """Пробелы по краям строки отбрасываются."""
    # Подготовка
    value = "  Мука  "

    # Действие
    result = Validator.validate_string(value, "name")

    # Проверка
    assert result == "Мука"


# Подготовка
@pytest.mark.parametrize("value", ["", "   "])
def test_validate_string_empty_or_blank_raises(value):
    """Пустая строка и строка из одних пробелов вызывают ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_string(value, "name")


# Подготовка
@pytest.mark.parametrize("value", [None, 123, 1.5, [], b"abc"])
def test_validate_string_not_string_raises(value):
    """Значение не строкового типа вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_string(value, "name")


def test_validate_string_max_length_boundary_returned():
    """Строка ровно максимальной длины проходит проверку."""
    # Подготовка
    value = "a" * 50

    # Действие
    result = Validator.validate_string(value, "name", max_length=50)

    # Проверка
    assert result == value


def test_validate_string_over_max_length_raises():
    """Строка длиннее максимальной вызывает ArgumentsException."""
    # Подготовка
    value = "a" * 51

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_string(value, "name", max_length=50)


def test_validate_string_spaces_not_counted_in_length():
    """Пробелы по краям не учитываются при проверке длины."""
    # Подготовка
    value = "  " + "a" * 50 + "  "

    # Действие
    result = Validator.validate_string(value, "name", max_length=50)

    # Проверка
    assert result == "a" * 50


# Подготовка
@pytest.mark.parametrize("value", [1, 1000, 0.001, 2.5])
def test_validate_positive_number_valid_value_returned(value):
    """Положительные целые и дробные числа возвращаются без изменений."""
    # Действие
    result = Validator.validate_positive_number(value, "factor")

    # Проверка
    assert result == value


# Подготовка
@pytest.mark.parametrize("value", [0, -1, -0.5, float("nan"), float("inf"), -float("inf"), True, None, "1000", [1]])
def test_validate_positive_number_invalid_value_raises(value):
    """Ноль, отрицательные, нечисловые, bool, NaN и бесконечность вызывают ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_positive_number(value, "factor")


# Подготовка
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1234567890", "1234567890"),
        ("123456789012", "123456789012"),
        ("0123456789", "0123456789"),
        ("  1234567890  ", "1234567890"),
    ],
)
def test_validate_digits_valid_value_returned(value, expected):
    """Строка из цифр допустимой длины возвращается, ведущие нули сохраняются, пробелы по краям отбрасываются."""
    # Действие
    result = Validator.validate_digits(value, "inn", (10, 12))

    # Проверка
    assert result == expected


# Подготовка
@pytest.mark.parametrize(
    "value",
    ["", "   ", "123456789", "12345678901", "1234567890123", "12345abc90", "1234 67890", None, 1234567890],
)
def test_validate_digits_invalid_value_raises(value):
    """Неверная длина, нецифровые символы и не строка вызывают ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_digits(value, "inn", (10, 12))


# Подготовка
@pytest.mark.parametrize("value", ["١٢٣٤٥٦٧٨٩٠", "²²²²²²²²²²"])
def test_validate_digits_non_ascii_digits_raises(value):
    """Не-ASCII «цифры» отклоняются: str.isdigit() считает их цифрами, но int() на «²» падает с ValueError."""
    # Подготовка
    assert value.isdigit()  # именно поэтому одной isdigit() недостаточно

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_digits(value, "inn", (10,))


def test_validate_instance_matching_type_returned():
    """Экземпляр ожидаемого типа возвращается тем же объектом."""
    # Подготовка
    value = ParentStub()

    # Действие
    result = Validator.validate_instance(value, ParentStub, "item", "Ожидается элемент")

    # Проверка
    assert result is value


def test_validate_instance_subclass_instance_returned():
    """Экземпляр подкласса ожидаемого типа проходит проверку."""
    # Подготовка
    value = ChildStub()

    # Действие
    result = Validator.validate_instance(value, ParentStub, "item", "Ожидается элемент")

    # Проверка
    assert result is value


# Подготовка
@pytest.mark.parametrize("value", [None, "item", 1, ParentStub])
def test_validate_instance_other_type_raises(value):
    """Значение другого типа (в том числе сам класс вместо экземпляра) вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_instance(value, ParentStub, "item", "Ожидается элемент")


def test_validate_instance_parent_instance_for_child_type_raises():
    """Экземпляр родительского класса не проходит проверку на дочерний тип."""
    # Подготовка
    value = ParentStub()

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        Validator.validate_instance(value, ChildStub, "item", "Ожидается дочерний элемент")


def test_validate_instance_error_contains_field_and_message():
    """Имя аргумента и пояснение попадают в текст ошибки."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        Validator.validate_instance(None, ParentStub, "item", "Ожидается элемент")
    assert "item" in str(exc_info.value)
    assert "Ожидается элемент" in str(exc_info.value)
