# Диаграммы последовательности

Диаграммы описывают, как работает реализованный код в `Src/`: порядок вызовов и ветки ошибок.
Классы и связи между ними — в [`ClassDiagram.md`](ClassDiagram.md).
При изменении порядка вызовов в менеджерах обновляйте соответствующую диаграмму.

## Получение экземпляра менеджера (Singleton)

Одинаково для любого менеджера: `SettingsManager()` и `StorageManager()` возвращают один и тот же объект.
Каждый конкретный менеджер реализует это в своём `__new__`, базовые классы Singleton не знают.
Состояние готовится в `__new__`, а не в конструкторе: конструктор Python вызывает при каждом обращении
к классу, а состояние нужно создать ровно один раз.

```mermaid
sequenceDiagram
    participant K as Клиент
    participant M as Класс менеджера
    participant I as Атрибут _instance класса

    K->>M: SettingsManager()
    M->>I: искать в cls.__dict__ экземпляр этого класса
    alt экземпляра ещё нет
        I-->>M: пусто
        M->>M: создать объект
        M->>M: _initialize() готовит состояние: is_loaded = False и своё состояние менеджера
        M->>I: сохранить экземпляр в _instance
    else экземпляр уже есть
        I-->>M: существующий экземпляр
    end
    M-->>K: единственный экземпляр класса
```

Если `_initialize()` упадёт, экземпляр в `_instance` не попадает: полусозданного менеджера не остаётся.
Экземпляр ищется в `cls.__dict__`, а не через обычное обращение к атрибуту, поэтому наследник
конкретного менеджера получает собственный экземпляр, а не экземпляр родителя.

## Загрузка настроек: SettingsManager.load()

Общий порядок задаёт `AbstractFileManager.load()`: сначала `_read()`, затем `convert()`.
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
    Note over S: путь = file_name без пробелов или settings.json в корне проекта
    S->>F: открыть и разобрать JSON
    alt файл недоступен, не UTF-8, не JSON или корень не объект
        F-->>S: ошибка чтения
        S->>S: предупреждение в лог
        opt файла нет
            S->>F: создать файл с настройками по умолчанию
            Note over S,F: ошибка записи только пишется в лог. Существующий файл не перезаписывается
        end
        S->>S: данные = настройки по умолчанию
    else данные прочитаны
        F-->>S: словарь с настройками
    end
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
```

Настройки по умолчанию подменяют только то, что не удалось прочитать. Если файл прочитан, но данные в нём
неверны, `convert()` бросает `OperationException`: некорректные настройки не маскируются значениями по умолчанию.
Настройки по умолчанию записаны в коде в формате файла и проходят тот же `convert()`.
Если в файле нет `is_first_start`, флаг принимается равным `True`.
Модель присваивается только целиком: при ошибке прежние настройки не затираются наполовину собранными.

## Загрузка хранилища и первый старт: StorageManager.load()

`StorageManager` зависит от менеджера настроек: `load(settings_manager)` принимает его параметром, по умолчанию
берёт единственный `SettingsManager`, и читает из него флаг `is_first_start`. Настройки сам `load()` не загружает,
поэтому `SettingsManager.load()` нужно вызвать до `StorageManager.load()`. С файлами `StorageManager`
не работает и сам реализует `load()`, наследуя `AbstractManager`. Внешнего источника данных пока нет:
чтение из SQLite появится позже.

```mermaid
sequenceDiagram
    participant K as Клиент
    participant St as StorageManager
    participant Se as SettingsManager
    participant C as UniqueCollection
    participant M as Модели

    K->>St: load(settings_manager)
    St->>St: is_loaded = False
    Note over St,Se: если менеджер не передан, берётся единственный SettingsManager()
    St->>Se: settings
    alt настройки не загружены
        Se-->>St: OperationException
        St-->>K: OperationException, is_loaded остаётся False
    else настройки есть
        Se-->>St: SettingsModel
        St->>St: _reset_collections() создаёт пустые коллекции
        alt is_first_start = False
            St->>St: is_loaded = True
            St-->>K: загрузка завершена, коллекции пусты
        else is_first_start = True
            St->>St: _fill_first_start_data()
            St->>M: фабрики единиц: create_kilogram (с граммом), create_liter (с миллилитром), create_piece
            St->>C: add() для 5 единиц
            St->>M: фабрики групп: мясные, молочные, овощи, бакалея, полуфабрикаты, блюда, упаковка
            St->>C: add() для 7 групп
            St->>M: фабрики номенклатуры: 3 старые позиции и 21 новая из Recipes.md
            Note over St,M: номенклатура получает те же объекты группы и единицы, что лежат в коллекциях, а не копии
            St->>C: add() для 24 позиций
            St->>M: фабрики складов: ресторана и производственного цеха
            St->>C: add() для 2 складов
            St->>M: фабрики карт RecipeModel.create_*(словарь наименование → номенклатура)
            Note over St,M: порядок: бульон, отварная говядина, зажарка, затем борщ
            loop для каждой карты
                St->>St: _add_recipe(): проверка циклов по вложенным картам
                St->>C: add() карты, ключ — id результата
            end
            alt дубликат по ключу коллекции или цикл между картами
                C-->>St: ArgumentsException
                St->>St: _reset_collections() очищает коллекции
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
