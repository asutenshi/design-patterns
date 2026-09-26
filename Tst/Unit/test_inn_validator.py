import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.inn_validator import InnValidator


# Подготовка
@pytest.mark.parametrize(
    "inn",
    ["7707083893", "7736207543", "1234567894", "0012345673", "500100732259", "123456789047", "001234567887"],
)
def test_validate_correct_inn_returned(inn):
    """ИНН из 10 и 12 цифр с верными контрольными цифрами возвращается без изменений, ведущие нули сохраняются."""
    # Действие
    result = InnValidator.validate(inn)

    # Проверка
    assert result == inn


def test_validate_surrounding_spaces_stripped():
    """Пробелы по краям ИНН отбрасываются."""
    # Подготовка
    inn = "  7707083893  "

    # Действие
    result = InnValidator.validate(inn)

    # Проверка
    assert result == "7707083893"


# Подготовка
@pytest.mark.parametrize("inn", ["1234567890", "7707083894", "123456789048", "123456789057", "500100732250"])
def test_validate_wrong_checksum_raises(inn):
    """ИНН с неверной контрольной цифрой (10-значный, 11-я или 12-я цифра 12-значного) вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        InnValidator.validate(inn)


# Подготовка
@pytest.mark.parametrize(
    "inn",
    ["", "   ", "123456789", "12345678901", "1234567890123", "77070838a3", None, 7707083893],
)
def test_validate_invalid_format_raises(inn):
    """Неверная длина, нецифровые символы и не строка вызывают ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        InnValidator.validate(inn)


# Подготовка
@pytest.mark.parametrize("inn", ["١٢٣٤٥٦٧٨٩٠", "²²²²²²²²²²"])
def test_validate_non_ascii_digits_raises_arguments_exception(inn):
    """Не-ASCII «цифры» дают ArgumentsException, а не ValueError из int() при расчёте контрольной суммы."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        InnValidator.validate(inn)


def test_validate_custom_field_in_message():
    """Имя аргумента из параметра field попадает в текст ошибки."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        InnValidator.validate("1234567890", field="tax_id")
    assert "tax_id" in str(exc_info.value)