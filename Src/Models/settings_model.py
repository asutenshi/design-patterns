from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.response_format import ResponseFormat
from Src.Models.organization_model import OrganizationModel


class SettingsModel(BaseEntity):
    """Настройки приложения: карточка организации, ответственные лица, флаг первого запуска, формат отчётов."""

    # Карточка организации
    _organization: OrganizationModel
    # Наименование директора
    _boss_name: str
    # Наименование главного бухгалтера
    _account_name: str
    # Флаг первого запуска
    _is_first_start: bool
    # Формат отчётов по умолчанию
    _response_format: ResponseFormat

    def __init__(
        self,
        organization: OrganizationModel,
        boss_name: str,
        account_name: str,
        is_first_start: bool = True,
        response_format: ResponseFormat = ResponseFormat.TXT,
    ) -> None:
        """Инициализирует настройки.

        :param organization: Карточка организации.
        :param boss_name: Наименование директора.
        :param account_name: Наименование главного бухгалтера.
        :param is_first_start: Флаг первого запуска.
        :param response_format: Формат отчётов по умолчанию.
        :raises ArgumentsException: Если любой из параметров не соответствует формату.
        """
        super().__init__()
        self.organization = organization
        self.boss_name = boss_name
        self.account_name = account_name
        self.is_first_start = is_first_start
        self.response_format = response_format

    @property
    def organization(self) -> OrganizationModel:
        """Возвращает карточку организации."""
        return self._organization

    @organization.setter
    def organization(self, value: OrganizationModel) -> None:
        """Устанавливает карточку организации.

        :param value: Новая карточка организации.
        :raises ArgumentsException: Если значение не является OrganizationModel.
        """
        self._organization = CommonValidator.validate_instance(
            value, OrganizationModel, "organization", "Ожидается карточка организации"
        )

    @property
    def boss_name(self) -> str:
        """Возвращает наименование директора."""
        return self._boss_name

    @boss_name.setter
    def boss_name(self, value: str) -> None:
        """Устанавливает наименование директора.

        :param value: Новое наименование директора.
        :raises ArgumentsException: Если значение не строка или пустое.
        """
        self._boss_name = CommonValidator.validate_string(value, "boss_name")

    @property
    def account_name(self) -> str:
        """Возвращает наименование главного бухгалтера."""
        return self._account_name

    @account_name.setter
    def account_name(self, value: str) -> None:
        """Устанавливает наименование главного бухгалтера.

        :param value: Новое наименование главного бухгалтера.
        :raises ArgumentsException: Если значение не строка или пустое.
        """
        self._account_name = CommonValidator.validate_string(value, "account_name")

    @property
    def is_first_start(self) -> bool:
        """Возвращает флаг первого запуска."""
        return self._is_first_start

    @is_first_start.setter
    def is_first_start(self, value: bool) -> None:
        """Устанавливает флаг первого запуска.

        :param value: Новое значение флага.
        :raises ArgumentsException: Если значение не bool.
        """
        self._is_first_start = CommonValidator.validate_instance(
            value, bool, "is_first_start", "Ожидается булево значение"
        )

    @property
    def response_format(self) -> ResponseFormat:
        """Возвращает формат отчётов по умолчанию."""
        return self._response_format

    @response_format.setter
    def response_format(self, value: ResponseFormat) -> None:
        """Устанавливает формат отчётов по умолчанию.

        :param value: Новый формат.
        :raises ArgumentsException: Если значение не ResponseFormat.
        """
        self._response_format = CommonValidator.validate_instance(
            value, ResponseFormat, "response_format", "Ожидается формат отчёта"
        )
