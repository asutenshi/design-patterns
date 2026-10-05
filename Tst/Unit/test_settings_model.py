import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.ownership_form import OwnershipForm
from Src.Models.organization_model import OrganizationModel
from Src.Models.settings_model import SettingsModel


def _organization() -> OrganizationModel:
    """Создаёт корректную карточку организации."""
    return OrganizationModel("Ромашка", "1234567894", "123456789", "12345678901234567890", OwnershipForm.LLC)


def test_init_valid_values_are_stored():
    """Корректные значения сохраняются в свойствах."""
    # Подготовка
    organization = _organization()

    # Действие
    settings = SettingsModel(organization, "  Иванов И. И. ", "Петрова А. А.", False)

    # Проверка
    assert settings.organization is organization
    assert settings.boss_name == "Иванов И. И."
    assert settings.account_name == "Петрова А. А."
    assert settings.is_first_start is False


def test_init_is_first_start_omitted_defaults_to_true():
    """Если флаг первого запуска не передан, он равен True."""
    # Действие
    settings = SettingsModel(_organization(), "Иванов И. И.", "Петрова А. А.")

    # Проверка
    assert settings.is_first_start is True


def test_organization_setter_not_organization_raises():
    """Значение, не являющееся OrganizationModel (например, строка), отклоняется."""
    # Подготовка
    settings = SettingsModel(_organization(), "Иванов И. И.", "Петрова А. А.")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        settings.organization = "Ромашка"  # pyright: ignore[reportAttributeAccessIssue]


# Подготовка
@pytest.mark.parametrize("field", ["boss_name", "account_name"])
def test_person_name_setter_blank_value_raises(field: str):
    """Имя из пробелов отклоняется. Остальные случаи проверены в test_common_validator."""
    # Подготовка
    settings = SettingsModel(_organization(), "Иванов И. И.", "Петрова А. А.")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        setattr(settings, field, "   ")


# Подготовка
@pytest.mark.parametrize("value", ["true", 1])
def test_is_first_start_setter_not_bool_raises(value: object):
    """Небулево значение флага первого запуска отклоняется."""
    # Подготовка
    settings = SettingsModel(_organization(), "Иванов И. И.", "Петрова А. А.")

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        settings.is_first_start = value  # pyright: ignore[reportAttributeAccessIssue]