# Диаграммы последовательности

Диаграммы описывают, как работает реализованный код в `Src/`: порядок вызовов и ветки ошибок.
Классы и связи между ними — в [`ClassDiagram.md`](ClassDiagram.md).
При изменении порядка вызовов в менеджерах обновляйте соответствующую диаграмму.

## Получение экземпляра менеджера (Singleton)

Одинаково для любого менеджера: `SettingsManager()` и `StorageManager()` возвращают один и тот же объект.
Состояние готовится в `AbstractManager.__new__`, а не в конструкторе: конструктор Python вызывает
при каждом обращении к классу, а состояние нужно создать ровно один раз.

```mermaid
sequenceDiagram
    participant K as Клиент
    participant M as Класс менеджера
    participant R as Реестр _instances

    K->>M: SettingsManager()
    M->>R: найти экземпляр этого класса
    alt экземпляра ещё нет
        R-->>M: пусто
        M->>M: создать объект, is_loaded = False, данные пусты
        M->>M: _initialize() готовит состояние наследника
        M->>R: сохранить экземпляр
    else экземпляр уже есть
        R-->>M: существующий экземпляр
    end
    M-->>K: единственный экземпляр класса
```

Если `_initialize()` упадёт, экземпляр в реестр не попадает: полусозданного менеджера не остаётся.

## Загрузка настроек: SettingsManager.load()

Общий порядок задаёт `AbstractManager.load()`: сначала `_read()`, затем `convert()`.
Флаг `is_loaded` становится `True` только после успешного `convert()`. Пока он `False`, свойство
`settings` бросает `OperationException`, даже если раньше настройки уже загружались.

```mermaid
sequenceDiagram
    participant K as Клиент
    participant S as SettingsManager
    participant F as Файл настроек
    participant O as OrganizationModel
    participant P as SettingsModel

    K->>S: load(file_name)
    S->>S: is_loaded = False, данные сброшены
    Note over S: путь = file_name без пробелов или settings.json
    S->>F: открыть и разобрать JSON
    alt файл недоступен, не UTF-8, не JSON или корень не объект
        F-->>S: ошибка чтения
        S-->>K: OperationException, is_loaded остаётся False
    else данные прочитаны
        F-->>S: словарь с настройками
        S->>S: convert()
        S->>O: OrganizationModel(name, inn, bic, account, OwnershipForm)
        O-->>S: карточка организации
        S->>P: SettingsModel(organization, boss_name, account_name, is_first_start)
        P-->>S: настройки
        alt нет ключа, неверный тип, неизвестная форма собственности или модель отклонила значение
            S-->>K: OperationException, is_loaded остаётся False
        else все данные корректны
            S->>S: _settings = модель, is_loaded = True
            S-->>K: загрузка завершена
        end
    end
```

Если в файле нет `is_first_start`, флаг принимается равным `True`.
Модель присваивается только целиком: при ошибке прежние настройки не затираются наполовину собранными.

## Загрузка хранилища и первый старт: StorageManager.load()

`StorageManager` зависит от настроек: флаг `is_first_start` он читает в `convert()` через `SettingsManager`.
Поэтому `SettingsManager.load()` нужно вызвать до `StorageManager.load()`. Внешнего источника данных пока нет:
`_read()` возвращает пустой словарь, чтение из SQLite появится позже.

```mermaid
sequenceDiagram
    participant K as Клиент
    participant St as StorageManager
    participant Se as SettingsManager
    participant C as UniqueCollection
    participant M as Модели

    K->>St: load()
    St->>St: is_loaded = False, данные сброшены
    St->>St: _read() возвращает пустой словарь
    St->>St: convert()
    St->>Se: settings
    alt настройки не загружены
        Se-->>St: OperationException
        St-->>K: OperationException, is_loaded остаётся False
    else настройки есть
        Se-->>St: SettingsModel
        St->>St: _initialize() создаёт пустые коллекции
        alt is_first_start = False
            St-->>K: загрузка завершена, коллекции пусты
        else is_first_start = True
            St->>St: _fill_first_start_data()
            St->>M: единицы: грамм, килограмм (база грамм), миллилитр, литр (база миллилитр), штука
            St->>C: add() для 5 единиц
            St->>M: группы: Мясные продукты, Молочные продукты, Упаковка
            St->>C: add() для 3 групп
            St->>M: номенклатура: Говядина, Молоко, Стакан
            Note over St,M: номенклатура получает те же объекты группы и единицы, что лежат в коллекциях, а не копии
            St->>C: add() для 3 позиций
            St->>M: склады: Склад ресторана, Склад производственного цеха
            St->>C: add() для 2 складов
            alt в коллекцию добавлен дубликат по name.casefold()
                C-->>St: ArgumentsException
                St->>St: _initialize() очищает коллекции
                St-->>K: OperationException, is_loaded остаётся False
            else дубликатов нет
                St->>St: is_loaded = True
                St-->>K: загрузка завершена
            end
        end
    end
```

Повторный `load()` каждый раз пересоздаёт коллекции, поэтому данные не дублируются. Если после первого
запуска в настройках сброшен `is_first_start`, повторная загрузка оставит коллекции пустыми.
