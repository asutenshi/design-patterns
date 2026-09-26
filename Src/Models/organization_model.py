from Src.Core.inn_validator import InnValidator
from Src.Core.named_entity import NamedEntity
from Src.Core.ownership_form import OwnershipForm
from Src.Core.validator import Validator


class OrganizationModel(NamedEntity):
    """Модель организации с банковскими реквизитами.

    ИНН, БИК и счёт хранятся строками, а не числами: в них бывают ведущие нули.
    ИНН проверяется вместе с контрольными цифрами (см. InnValidator), БИК и счёт —
    только по формату (длина и цифры). Длина ИНН не зависит от формы собственности.

    Поддерживаются только российские реквизиты. Иностранные банки используют SWIFT/BIC
    и IBAN — это другие поля с другим форматом, а не вариант БИК и расчётного счёта.
    Если такая потребность появится, для них нужны отдельные поля.
    """

    # Длина БИК
    BIC_LENGTH: int = 9
    # Длина расчётного счёта
    ACCOUNT_LENGTH: int = 20

    # ИНН организации
    _inn: str
    # БИК банка организации
    _bic: str
    # Расчётный счёт организации
    _account: str
    # Форма собственности
    _ownership_form: OwnershipForm

    def __init__(self, name: str, inn: str, bic: str, account: str, ownership_form: OwnershipForm) -> None:
        """Инициализирует организацию.

        :param name: Наименование организации.
        :param inn: ИНН — 10 или 12 цифр с верной контрольной суммой.
        :param bic: БИК — 9 цифр.
        :param account: Расчётный счёт — 20 цифр.
        :param ownership_form: Форма собственности.
        :raises ArgumentsException: Если любой из параметров не соответствует формату.
        """
        super().__init__(name)
        self.inn = inn
        self.bic = bic
        self.account = account
        self.ownership_form = ownership_form

    @property
    def inn(self) -> str:
        """Возвращает ИНН организации."""
        return self._inn

    @inn.setter
    def inn(self, value: str) -> None:
        """Устанавливает ИНН организации.

        :param value: Новый ИНН — строка из 10 или 12 цифр с верной контрольной суммой.
        :raises ArgumentsException: Если значение не строка из 10 или 12 цифр
            или контрольные цифры не совпадают.
        """
        self._inn = InnValidator.validate(value, "inn")

    @property
    def bic(self) -> str:
        """Возвращает БИК банка организации."""
        return self._bic

    @bic.setter
    def bic(self, value: str) -> None:
        """Устанавливает БИК банка организации.

        :param value: Новый БИК — строка из 9 цифр.
        :raises ArgumentsException: Если значение не строка из 9 цифр.
        """
        self._bic = Validator.validate_digits(value, "bic", (self.BIC_LENGTH,))

    @property
    def account(self) -> str:
        """Возвращает расчётный счёт организации."""
        return self._account

    @account.setter
    def account(self, value: str) -> None:
        """Устанавливает расчётный счёт организации.

        :param value: Новый счёт — строка из 20 цифр.
        :raises ArgumentsException: Если значение не строка из 20 цифр.
        """
        self._account = Validator.validate_digits(value, "account", (self.ACCOUNT_LENGTH,))

    @property
    def ownership_form(self) -> OwnershipForm:
        """Возвращает форму собственности организации."""
        return self._ownership_form

    @ownership_form.setter
    def ownership_form(self, value: OwnershipForm) -> None:
        """Устанавливает форму собственности организации.

        :param value: Новая форма собственности.
        :raises ArgumentsException: Если значение не является OwnershipForm.
        """
        self._ownership_form = Validator.validate_instance(
            value, OwnershipForm, "ownership_form", "Ожидается форма собственности"
        )