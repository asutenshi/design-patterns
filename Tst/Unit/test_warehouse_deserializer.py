import uuid
from collections.abc import Callable

import pytest
from Src.Core.exception import ArgumentsException
from Src.Logics.deserializer_factory import DeserializerFactory
from Src.Models.warehouse_model import WarehouseModel


def test_deserialize_warehouse_builds_model_with_id():
    """Склад собирается из наименования, идентификатор берётся из данных."""
    # Подготовка
    warehouse_id = uuid.uuid4()

    # Действие
    warehouse = DeserializerFactory().deserialize(WarehouseModel, {"id": str(warehouse_id), "name": "Склад ресторана"})

    # Проверка
    assert warehouse.name == "Склад ресторана"
    assert warehouse.id == warehouse_id


def test_deserialize_warehouse_without_name_raises():
    """Без наименования склад не собирается: ArgumentsException с именем поля."""
    # Действие и проверка
    with pytest.raises(ArgumentsException) as exc_info:
        DeserializerFactory().deserialize(WarehouseModel, {"id": str(uuid.uuid4()), "title": "Склад"})
    assert "name" in str(exc_info.value)


def test_deserialize_roundtrip_first_start_warehouses_match_stored(
    first_start_storage, roundtrip: Callable[..., object]
):
    """Склады хранилища после выгрузки и загрузки совпадают с исходными по id и наименованию."""
    for original in first_start_storage.warehouses:
        # Действие
        loaded = roundtrip(original, WarehouseModel)

        # Проверка
        assert isinstance(loaded, WarehouseModel)
        assert loaded == original
        assert loaded.name == original.name
