from Src.Core.base_entity import base_entity
from Src.Core.exception import arguments_exception

import uuid
import pytest

class test_entity(base_entity):
    pass
    

def test_base_entity_get_id_not_null():
    # Подготовка
    entity = test_entity('a')
    
    # Действие
    result = entity.id
    
    # Проверка
    assert result != None
    print(result)

def test_base_entity_uniq_id():
    # Подготовка
    entity1 = test_entity('a')
    entity2 = test_entity('b')
    
    # Действие
    id1 = entity1.id
    id2 = entity2.id
    
    # Проверка
    assert id1 != id2
    print(id1)
    print(id2)

def test_base_entity_eq():
    # Подготовка
    entity1 = test_entity('a')
    entity2 = test_entity('b')
    new_id = uuid.uuid4()

    # Действие
    entity1.id = new_id
    entity2.id = new_id

    # Проверка
    assert entity1 == entity2
    print(entity1.id)
    print(entity2.id)

def test_base_entity_void_name() -> None:
    # Подготовка: некорректные имена (пустая строка и None) передаются напрямую в конструктор

    # Действие и проверка: создание сущности с пустой строкой вызывает исключение
    with pytest.raises(arguments_exception):
        entity = test_entity('')

    # Действие и проверка: создание сущности с None вызывает исключение
    with pytest.raises(arguments_exception):
        entity = test_entity(None)
