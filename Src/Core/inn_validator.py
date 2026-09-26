from Src.Core.exception import ArgumentsException
from Src.Core.validator import Validator


class InnValidator:
    """Проверка ИНН: формат (10 или 12 цифр) и контрольные цифры.

    Контрольные цифры считаются по алгоритму ФНС: сумма произведений цифр на веса
    по модулю 11, затем по модулю 10.

    Выделен в отдельный класс, чтобы ИНН проверялся одинаково везде, где он появится
    (организация, в перспективе контрагент), и тестировался независимо от моделей.
    Возвращает обычную строку, а не объект-значение: так поле остаётся ``str``
    и не требует преобразований при сериализации. Если у ИНН появится поведение
    (например, «ИП или юрлицо»), поверх этого класса можно сделать объект-значение.
    """

    # Допустимые длины ИНН: 10 — юридическое лицо, 12 — физическое лицо и ИП
    LENGTHS: tuple[int, ...] = (10, 12)

    # Веса для 10-й цифры 10-значного ИНН
    _WEIGHTS_10: tuple[int, ...] = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    # Веса для 11-й цифры 12-значного ИНН
    _WEIGHTS_12_FIRST: tuple[int, ...] = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    # Веса для 12-й цифры 12-значного ИНН
    _WEIGHTS_12_SECOND: tuple[int, ...] = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

    @staticmethod
    def validate(value: object, field: str = "inn") -> str:
        """Проверяет ИНН и возвращает его без пробелов по краям.

        :param value: Проверяемое значение.
        :param field: Имя аргумента для текста ошибки.
        :return: ИНН — строка из 10 или 12 цифр.
        :raises ArgumentsException: Если значение не строка из 10 или 12 ASCII-цифр
            или контрольные цифры не совпадают.
        """
        inn = Validator.validate_digits(value, field, InnValidator.LENGTHS)

        if len(inn) == 10:
            is_valid = InnValidator._check_digit(inn, InnValidator._WEIGHTS_10) == int(inn[9])
        else:
            is_valid = (
                InnValidator._check_digit(inn, InnValidator._WEIGHTS_12_FIRST) == int(inn[10])
                and InnValidator._check_digit(inn, InnValidator._WEIGHTS_12_SECOND) == int(inn[11])
            )
        if not is_valid:
            raise ArgumentsException(field, "Контрольная цифра ИНН не совпадает")

        return inn

    @staticmethod
    def _check_digit(digits: str, weights: tuple[int, ...]) -> int:
        """Считает контрольную цифру по первым len(weights) цифрам строки.

        :param digits: Строка из ASCII-цифр. Это гарантирует Validator.validate_digits:
            для других Unicode-цифр int() мог бы бросить ValueError или принять их молча.
        :param weights: Веса для соответствующих цифр.
        :return: Контрольная цифра от 0 до 9.
        """
        total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
        return total % 11 % 10