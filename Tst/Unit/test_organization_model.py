import pytest
from Src.Core.base_entity import BaseEntity
from Src.Core.exception import ArgumentsException
from Src.Core.ownership_form import OwnershipForm
from Src.Models.organization_model import OrganizationModel

VALID_INN = "1234567894"
VALID_INN_12 = "123456789047"
VALID_BIC = "123456789"
VALID_ACCOUNT = "12345678901234567890"


def make_organization(**overrides) -> OrganizationModel:
    """Создаёт организацию с корректными данными, подменяя переданные параметры."""
    params = {
        "name": "Ромашка",
        "inn": VALID_INN,
        "bic": VALID_BIC,
        "account": VALID_ACCOUNT,
        "ownership_form": OwnershipForm.LLC,
    }
    params.update(overrides)
    return OrganizationModel(**params)


def test_init_valid_params_fields_set():
    """Организация создаётся с переданными значениями всех полей и заданным идентификатором."""
    # Подготовка
    ownership_form = OwnershipForm.LLC

    # Действие
    organization = OrganizationModel("Ромашка", VALID_INN, VALID_BIC, VALID_ACCOUNT, ownership_form)

    # Проверка
    assert organization.name == "Ромашка"
    assert organization.inn == VALID_INN
    assert organization.bic == VALID_BIC
    assert organization.account == VALID_ACCOUNT
    assert organization.ownership_form is ownership_form
    assert organization.id is not None


def test_init_any_instance_is_base_entity():
    """Организация является наследником BaseEntity."""
    # Действие
    result = isinstance(make_organization(), BaseEntity)

    # Проверка
    assert result is True


# Подготовка
@pytest.mark.parametrize("ownership_form", list(OwnershipForm))
def test_init_each_ownership_form_created(ownership_form):
    """Организация создаётся с каждой из допустимых форм собственности."""
    # Действие
    organization = make_organization(ownership_form=ownership_form)

    # Проверка
    assert organization.ownership_form is ownership_form


# Подготовка
@pytest.mark.parametrize("inn", [VALID_INN, VALID_INN_12])
def test_init_valid_inn_length_created(inn):
    """ИНН из 10 цифр (юрлицо) и из 12 цифр (ИП) с верной контрольной суммой допустим."""
    # Действие
    organization = make_organization(inn=inn)

    # Проверка
    assert organization.inn == inn


def test_init_leading_zeros_preserved():
    """Ведущие нули в ИНН, БИК и счёте сохраняются."""
    # Действие
    organization = make_organization(inn="0012345673", bic="004452522", account="00000000000000000001")

    # Проверка
    assert organization.inn == "0012345673"
    assert organization.bic == "004452522"
    assert organization.account == "00000000000000000001"


def test_init_requisites_with_spaces_stripped():
    """Пробелы по краям ИНН, БИК и счёта отбрасываются."""
    # Действие
    organization = make_organization(inn=f"  {VALID_INN} ", bic=f" {VALID_BIC}  ", account=f"{VALID_ACCOUNT} ")

    # Проверка
    assert organization.inn == VALID_INN
    assert organization.bic == VALID_BIC
    assert organization.account == VALID_ACCOUNT


# Подготовка
@pytest.mark.parametrize("name", ["", "   ", None, 123])
def test_init_invalid_name_raises(name):
    """Пустое, состоящее из пробелов или не строковое наименование вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(name=name)


# Подготовка
@pytest.mark.parametrize("inn", ["", "123456789", "12345678901", "1234567890123", "12345abc90", None, 1234567894])
def test_init_invalid_inn_raises(inn):
    """ИНН неверной длины, с нецифровыми символами или не строка вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(inn=inn)


# Подготовка
@pytest.mark.parametrize("inn", ["1234567890", "123456789048", "123456789057"])
def test_init_inn_wrong_checksum_raises(inn):
    """ИНН правильной длины, но с неверной контрольной цифрой вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(inn=inn)


# Подготовка
@pytest.mark.parametrize("bic", ["", "12345678", "1234567890", "12345abc9", None, 123456789])
def test_init_invalid_bic_raises(bic):
    """БИК неверной длины, с нецифровыми символами или не строка вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(bic=bic)


# Подготовка
@pytest.mark.parametrize("account", ["", "1234567890123456789", "123456789012345678901", "1234567890123456789a", None])
def test_init_invalid_account_raises(account):
    """Счёт неверной длины, с нецифровыми символами или не строка вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(account=account)


# Подготовка
@pytest.mark.parametrize("ownership_form", ["ООО", "LLC", None, 1])
def test_init_invalid_ownership_form_raises(ownership_form):
    """Форма собственности не из OwnershipForm (в том числе строка) вызывает ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        make_organization(ownership_form=ownership_form)


def test_setters_valid_values_updated():
    """Сеттеры обновляют ИНН, БИК, счёт и форму собственности."""
    # Подготовка
    organization = make_organization()

    # Действие
    organization.inn = VALID_INN_12
    organization.bic = "987654321"
    organization.account = "09876543210987654321"
    organization.ownership_form = OwnershipForm.SOLE_PROPRIETOR

    # Проверка
    assert organization.inn == VALID_INN_12
    assert organization.bic == "987654321"
    assert organization.account == "09876543210987654321"
    assert organization.ownership_form is OwnershipForm.SOLE_PROPRIETOR


# Подготовка
@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("inn", "123"),
        ("inn", "1234567890"),
        ("bic", "123"),
        ("account", "123"),
        ("ownership_form", "ООО"),
    ],
)
def test_setters_invalid_value_raises_and_keeps_old(attribute, value):
    """Некорректное значение в сеттере вызывает ArgumentsException и не меняет прежнее значение."""
    # Подготовка
    organization = make_organization()
    old_value = getattr(organization, attribute)

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        setattr(organization, attribute, value)
    assert getattr(organization, attribute) == old_value


def test_init_romashka_example_demonstration():
    """Демонстрация создания организации ООО «Ромашка» и смены расчётного счёта."""
    # Подготовка
    organization = OrganizationModel("Ромашка", "1234567894", "123456789", "40702810400000000001", OwnershipForm.LLC)

    # Действие
    organization.account = "40702810500000000002"

    # Проверка
    assert organization.ownership_form.value == "ООО"
    assert organization.account == "40702810500000000002"