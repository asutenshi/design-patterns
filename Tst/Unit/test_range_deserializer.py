import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException, OperationException
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.range_model import RangeModel

_GRAM_ID = str(uuid.uuid4())
_KILOGRAM_ID = str(uuid.uuid4())


def _gram() -> dict[str, object]:
    """Данные базовой единицы: она ссылается сама на себя."""
    return {"id": _GRAM_ID, "name": "грамм", "base": {"id": _GRAM_ID}, "factor": 1, "is_base": True}


def _kilogram() -> dict[str, object]:
    """Данные производной единицы: базовая вложена полным словарём."""
    return {"id": _KILOGRAM_ID, "name": "килограмм", "base": _gram(), "factor": 1000, "is_base": False}


def test_deserialize_base_range_refers_to_itself():
    """Базовая единица со ссылкой на саму себя собирается без бесконечной рекурсии: её base — она сама."""
    # Действие
    gram = DeserializerFactory().deserialize(RangeModel, _gram())

    # Проверка
    assert gram.name == "грамм"
    assert gram.factor == 1
    assert gram.is_base
    assert gram.base is gram
    assert gram.id == uuid.UUID(_GRAM_ID)


def test_deserialize_derived_range_builds_base_recursively():
    """Производная единица собирает вложенную базовую единицу рекурсивно, id обеих сохраняются."""
    # Действие
    kilogram = DeserializerFactory().deserialize(RangeModel, _kilogram())

    # Проверка
    assert kilogram.name == "килограмм"
    assert kilogram.factor == 1000
    assert not kilogram.is_base
    assert kilogram.base.name == "грамм"
    assert kilogram.base.is_base
    assert kilogram.id == uuid.UUID(_KILOGRAM_ID)
    assert kilogram.base.id == uuid.UUID(_GRAM_ID)


def test_deserialize_derived_range_with_base_reference_after_base_uses_same_object():
    """Производная единица, чья база записана ссылкой на уже собранную базовую, использует тот же объект."""
    # Подготовка
    ton_id = str(uuid.uuid4())
    ton = {"id": ton_id, "name": "тонна", "base": {"id": _GRAM_ID}, "factor": 1_000_000}
    factory = DeserializerFactory()
    deserializer = factory.create(RangeModel)

    # Действие
    gram = deserializer.deserialize(_gram())
    result = deserializer.deserialize(ton)

    # Проверка
    assert isinstance(result, RangeModel)
    assert result.base is gram


def test_deserialize_derived_range_with_unknown_base_reference_raises():
    """База записана ссылкой на единицу, которой нет в данных, — OperationException."""
    # Подготовка
    data = {"id": _KILOGRAM_ID, "name": "килограмм", "base": {"id": _GRAM_ID}, "factor": 1000}

    # Действие и проверка
    with pytest.raises(OperationException):
        DeserializerFactory().deserialize(RangeModel, data)


# Подготовка
@pytest.mark.parametrize("field", ["name", "factor", "base"])
def test_deserialize_missing_field_raises(field: str):
    """Отсутствие любого обязательного поля вызывает ArgumentsException с его именем."""
    # Подготовка
    data = _kilogram()
    del data[field]

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(RangeModel, data)
    assert field in str(exc_info.value)


def test_deserialize_base_range_with_factor_not_one_raises():
    """Ограничения модели действуют и при загрузке: у базовой единицы коэффициент должен быть равен 1."""
    # Подготовка
    data = _gram()
    data["factor"] = 5

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(RangeModel, data)


def test_deserialize_base_is_not_a_dict_raises():
    """Поле base не словарь — ArgumentsException."""
    # Подготовка
    data = _kilogram()
    data["base"] = "грамм"

    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(RangeModel, data)


def test_deserialize_roundtrip_first_start_ranges_match_stored(first_start_storage, roundtrip: Callable[..., object]):
    """Единицы хранилища после выгрузки и загрузки совпадают с исходными по id, наименованию, коэффициенту и базе."""
    # Подготовка
    stored = first_start_storage.ranges

    for original in stored:
        # Действие
        loaded = roundtrip(original, RangeModel)

        # Проверка
        assert isinstance(loaded, RangeModel)
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.factor == original.factor
        assert loaded.is_base == original.is_base
        assert loaded.base == original.base
