import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.nomenclature_group_model import NomenclatureGroupModel


def test_deserialize_group_builds_model_with_id():
    """Группа собирается из наименования, идентификатор берётся из данных."""
    # Подготовка
    group_id = uuid.uuid4()

    # Действие
    group = DeserializerFactory().deserialize(NomenclatureGroupModel, {"id": str(group_id), "name": "Овощи"})

    # Проверка
    assert group.name == "Овощи"
    assert group.id == group_id


def test_deserialize_group_without_name_raises():
    """Без наименования группа не собирается: ArgumentsException с именем поля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(NomenclatureGroupModel, {"id": str(uuid.uuid4()), "title": "Овощи"})
    assert "name" in str(exc_info.value)


def test_deserialize_group_empty_name_raises():
    """Правила модели действуют и при загрузке: пустое наименование недопустимо."""
    # Действие и проверка
    with pytest.raises(ArgumentsException):
        DeserializerFactory().deserialize(NomenclatureGroupModel, {"name": "  "})


def test_deserialize_roundtrip_first_start_groups_match_stored(first_start_storage, roundtrip: Callable[..., object]):
    """Группы хранилища после выгрузки и загрузки совпадают с исходными по id и наименованию."""
    for original in first_start_storage.nomenclature_groups:
        # Действие
        loaded = roundtrip(original, NomenclatureGroupModel)

        # Проверка
        assert isinstance(loaded, NomenclatureGroupModel)
        assert loaded == original
        assert loaded.name == original.name
