import math

from Src.Core.exception import ArgumentsException


class CommonValidator:
    """Набор общих проверок входных значений для моделей."""

    @staticmethod
    def validate_string(value: object, field: str, max_length: int | None = None) -> str:
        """Проверяет строку и возвращает её без пробелов по краям.

        :param value: Проверяемое значение.
        :param field: Имя аргумента для текста ошибки.
        :param max_length: Максимально допустимая длина строки, None — без ограничения.
        :return: Очищенная от пробелов по краям строка.
        :raises ArgumentsException: Если значение не строка, пустое, состоит из пробелов
            или длиннее max_length.
        """
        if not isinstance(value, str):
            raise ArgumentsException(field, "Ожидается строка")

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ArgumentsException(field, "Значение не может быть пустым")
        if max_length is not None and len(cleaned_value) > max_length:
            raise ArgumentsException(field, f"Длина не должна превышать {max_length} символов")

        return cleaned_value

    @staticmethod
    def validate_positive_number(value: object, field: str) -> int | float:
        """Проверяет, что значение — конечное число строго больше нуля.

        :param value: Проверяемое значение.
        :param field: Имя аргумента для текста ошибки.
        :return: Проверенное число.
        :raises ArgumentsException: Если значение не число (в том числе bool),
            не конечное (NaN, бесконечность) или не больше нуля.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ArgumentsException(field, "Ожидается число")
        if isinstance(value, float) and not math.isfinite(value):
            raise ArgumentsException(field, "Значение должно быть конечным числом")
        if value <= 0:
            raise ArgumentsException(field, "Значение должно быть больше нуля")

        return value

    @staticmethod
    def validate_digits(value: object, field: str, lengths: tuple[int, ...]) -> str:
        """Проверяет, что значение — строка из ASCII-цифр допустимой длины.

        Допускаются только цифры 0–9. ``str.isdigit()`` этого не гарантирует: он истинен
        и для других Unicode-цифр (арабо-индийских «١٢٣», надстрочных «²»). Такие символы
        отклоняются намеренно:

        - ``int("²")`` бросает ValueError, поэтому вычисления над цифрами (например,
          контрольная сумма ИНН) упали бы стандартным исключением, а не ArgumentsException;
        - ``int("١")`` принимает молча, и нестандартный номер попал бы в хранилище
          и во внешние системы.

        Это защитное требование проекта, в ТЗ его нет.

        :param value: Проверяемое значение.
        :param field: Имя аргумента для текста ошибки.
        :param lengths: Допустимые длины строки.
        :return: Очищенная от пробелов по краям строка цифр.
        :raises ArgumentsException: Если значение не строка, пустое, содержит не только
            ASCII-цифры или его длина не входит в lengths.
        """
        cleaned_value = CommonValidator.validate_string(value, field)
        # isdigit() пропускает не-ASCII цифры, поэтому isascii() обязателен, см. docstring
        if not (cleaned_value.isascii() and cleaned_value.isdigit()):
            raise ArgumentsException(field, "Ожидаются только цифры")
        if len(cleaned_value) not in lengths:
            expected = " или ".join(str(length) for length in lengths)
            raise ArgumentsException(field, f"Ожидается цифр: {expected}")

        return cleaned_value

    @staticmethod
    def validate_instance[T](value: object, expected_type: type[T], field: str, message: str) -> T:
        """Проверяет, что значение является экземпляром ожидаемого типа.

        Параметр value имеет тип object намеренно: проверка защищает от неверно переданных
        аргументов в рантайме, и статический анализатор не должен считать её лишней.

        :param value: Проверяемое значение.
        :param field: Имя аргумента для текста ошибки.
        :param expected_type: Ожидаемый тип (экземпляры подклассов тоже допустимы).
        :param message: Пояснение для текста ошибки.
        :return: То же значение, суженное до expected_type.
        :raises ArgumentsException: Если значение не является экземпляром expected_type.
        """
        if not isinstance(value, expected_type):
            raise ArgumentsException(field, message)

        return value
