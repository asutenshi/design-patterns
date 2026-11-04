import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException
from Src.Core.nomenclature_type import NomenclatureType
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.nomenclature_model import NomenclatureModel

_GRAM_ID = str(uuid.uuid4())
_KILOGRAM_ID = str(uuid.uuid4())
_GROUP_ID = str(uuid.uuid4())


def _kilogram() -> dict[str, object]:
    """Данные килограмма с вложенным граммом."""
    gram = {"id": _GRAM_ID, "name": "грамм", "base": {"id": _GRAM_ID}, "factor": 1, "is_base": True}
    return {"id": _KILOGRAM_ID, "name": "килограмм", "base": gram, "factor": 1000, "is_base": False}


def _beef(**changes: object) -> dict[str, object]:
    """Данные номенклатуры «Говядина» с вложенными группой и единицей, поля можно заменить."""
    data: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "name": "Говядина",
        "full_name": "Говядина охлаждённая",
        "group": {"id": _GROUP_ID, "name": "Мясные продукты"},
        "range": _kilogram(),
        "type": "сырьё",
        "grams_per_base_unit": 1,
    }
    data.update(changes)
    return data


def test_deserialize_nomenclature_builds_nested_models_recursively():
    """Номенклатура собирает группу и единицу измерения (вместе с её базовой единицей) рекурсивно."""
    # Подготовка
    data = _beef()

    # Действие
    beef = DeserializerFactory().deserialize(NomenclatureModel, data)

    # Проверка
    assert beef.name == "Говядина"
    assert beef.full_name == "Говядина охлаждённая"
    assert beef.group.name == "Мясные продукты"
    assert beef.group.id == uuid.UUID(_GROUP_ID)
    assert beef.range.name == "килограмм"
    assert beef.range.base.name == "грамм"
    assert beef.type is NomenclatureType.RAW_MATERIAL
    assert beef.grams_per_base_unit == 1
    assert str(beef.id) == data["id"]


def test_deserialize_nomenclature_shared_range_is_one_object():
    """Единица, вложенная полным словарём и ссылкой, — один объект, а не копии (кэш по id)."""
    # Подготовка
    factory = DeserializerFactory()
    deserializer = factory.create(NomenclatureModel)

    # Действие
    first = deserializer.deserialize(_beef(name="Говядина"))
    second = deserializer.deserialize(_beef(name="Кости", range={"id": _KILOGRAM_ID}))

    # Проверка
    assert isinstance(first, NomenclatureModel)
    assert isinstance(second, NomenclatureModel)
    assert second.range is first.range


# Подготовка
@pytest.mark.parametrize("field", ["name", "full_name", "group", "range", "type", "grams_per_base_unit"])
def test_deserialize_missing_field_raises(field: str):
    """Отсутствие любого обязательного поля вызывает ArgumentsException с его именем."""
    # Подготовка
    data = _beef()
    del data[field]

    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(NomenclatureModel, data)
    assert field in str(exc_info.value)


def test_deserialize_unknown_type_raises():
    """Тип, которого нет в перечислении, — ArgumentsException."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(NomenclatureModel, _beef(type="еда"))
    assert "type" in str(exc_info.value)


def test_deserialize_non_positive_weight_raises():
    """Правила модели действуют и при загрузке: вес базовой единицы должен быть больше нуля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(NomenclatureModel, _beef(grams_per_base_unit=0))


def test_deserialize_roundtrip_first_start_nomenclatures_match_stored(
    first_start_storage, roundtrip: Callable[..., object]
):
    """Вся номенклатура хранилища после выгрузки и загрузки совпадает с исходной по всем полям."""
    for original in first_start_storage.nomenclatures:
        # Действие
        loaded = roundtrip(original, NomenclatureModel)

        # Проверка
        assert isinstance(loaded, NomenclatureModel)
        assert loaded == original
        assert loaded.name == original.name
        assert loaded.full_name == original.full_name
        assert loaded.group == original.group
        assert loaded.range == original.range
        assert loaded.range.base == original.range.base
        assert loaded.type is original.type
        assert loaded.grams_per_base_unit == original.grams_per_base_unit
