# Диаграммы классов

Диаграммы описывают реализованный код в `Src/`, а не планы из `Docs/DomainEntities.md`.
При добавлении, переименовании или удалении класса обновляйте соответствующую диаграмму.
Mermaid отображается в GitHub и в IDE с поддержкой Markdown.

## Модели

Все модели лежат в `Src/Models/`, базовые классы — в `Src/Core/`.
Стрелка с пустым треугольником — наследование, обычная стрелка — хранимая ссылка на другую модель.

Корень всех моделей — `AbstractModel`: тип модели `model_type` (полное имя класса, его пишет в JSON
`ConverterFactory`) и абстрактный фабричный метод `from_dict` для загрузки из JSON. От него наследуются
`BaseEntity` (сущности с `id`) и `IngredientModel` (строка состава без `id`). В конструкторах моделей
`from_dict` вызывает только сама модель, вложенные модели он получает уже собранными. Наследники
регистрируются в реестре по `model_type` при импорте модуля, `resolve_type` находит по нему класс.
`from_dict` есть у каждой модели, на диаграмме он не повторяется.

```mermaid
classDiagram
    direction TB

    class AbstractModel {
        <<abstract>>
        +TYPE_FIELD$: str
        -_registry$: dict~str, type~
        +model_type: str
        +from_dict(data)* Self
        +resolve_type(model_type)$ type~AbstractModel~
        +type_name(model_class)$ str
    }

    note for AbstractModel "from_dict — абстрактный метод класса (@classmethod). Реестр наследников заполняется в __init_subclass__. resolve_type отвергает неизвестный, абстрактный и нестроковый тип"

    class BaseEntity {
        <<abstract>>
        +id: UUID
        +replace_state(other) None
    }

    note for BaseEntity "Равенство и хэш определяются по id и типу. replace_state копирует состояние другой сущности того же типа, чтобы менять сущность на месте: ссылки на неё остаются верными. Прямые ссылки модели на другие сущности находит ReferenceScanner"

    class NamedEntity {
        <<abstract>>
        +name: str
        +name_key() str
    }

    note for NamedEntity "name_key — ключ уникальности по наименованию без учёта регистра, функция ключа UniqueCollection"

    class RangeModel {
        +base: RangeModel
        +factor: int | float
        +is_base: bool
        +create_kilogram()$ RangeModel
        +create_liter()$ RangeModel
        +create_piece()$ RangeModel
    }

    class NomenclatureModel {
        +NAME_MAX_LENGTH = 50
        +FULL_NAME_MAX_LENGTH = 255
        +full_name: str
        +group: NomenclatureGroupModel
        +range: RangeModel
        +type: NomenclatureType
        +grams_per_base_unit: int | float
        +create_raw_material(name, full_name, group, range, grams_per_base_unit)$ NomenclatureModel
        +create_semi_finished(name, full_name, group, range, grams_per_base_unit)$ NomenclatureModel
        +create_dish(name, full_name, group, range, grams_per_base_unit)$ NomenclatureModel
        +create_packaging(name, full_name, group, range, grams_per_base_unit)$ NomenclatureModel
    }

    class NomenclatureType {
        <<enumeration>>
        RAW_MATERIAL
        PRODUCT
        SEMI_FINISHED
        DISH
        PACKAGING
    }

    class IngredientModel {
        +nomenclature: NomenclatureModel
        +quantity: int | float
        +loss_ratio: int | float
        +base: tuple~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +scaled(factor) IngredientModel
        +contains(nomenclature) bool
        +nomenclature_key() UUID
    }

    note for IngredientModel "Строка состава карты, без id (паттерн Компоновщик в одном классе). Пустое base — сырьё или упаковка, вес из количества и grams_per_base_unit. Непустое base — полуфабрикат: снимок карты под это количество, вес — сумма base. base задаётся в конструкторе и копируется, смена quantity масштабирует его. Веса вычисляются при каждом обращении. О картах не знает"

    class NomenclatureCatalog {
        +get(name) NomenclatureModel
    }

    note for NomenclatureCatalog "Справочник номенклатуры: поиск по наименованию. Не владеет позициями, возвращает те же экземпляры. Повтор наименования отвергается"

    class RecipeModel {
        +RESULT_TYPES: frozenset~NomenclatureType~
        +result: NomenclatureModel
        +output_quantity: int | float
        +cooking_time_minutes: int | float
        +steps: list~str~
        +items: list~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +gross_weight_for(output_quantity) float
        +net_weight_for(output_quantity) float
        +add_item(item) None
        +remove_item(nomenclature) None
        +as_ingredient(quantity, loss_ratio) IngredientModel
        +result_key() UUID
        +create_beef_bouillon(catalog)$ RecipeModel
        +create_boiled_beef(catalog)$ RecipeModel
        +create_beet_fry(catalog)$ RecipeModel
        +create_borscht(catalog, bouillon?, boiled_beef?, beet_fry?)$ RecipeModel
    }

    note for RecipeModel "Результат (полуфабрикат или блюдо) только для чтения. Ингредиенты состава уникальны по номенклатуре. Веса брутто и нетто — сумма по ингредиентам, рекурсия получается сама. as_ingredient собирает снимок карты для состава другой карты. add_item отвергает строку, в дереве которой есть результат карты. gross_weight_for и net_weight_for масштабируют веса под заданный выход. Фабрики карт принимают NomenclatureCatalog. create_borscht сам создаёт не переданные карты полуфабрикатов, ошибки не скрывает"

    class NomenclatureGroupModel {
        +create_meat()$ NomenclatureGroupModel
        +create_dairy()$ NomenclatureGroupModel
        +create_vegetables()$ NomenclatureGroupModel
        +create_grocery()$ NomenclatureGroupModel
        +create_semi_finished()$ NomenclatureGroupModel
        +create_dishes()$ NomenclatureGroupModel
        +create_packaging()$ NomenclatureGroupModel
    }

    class WarehouseModel {
        +create_restaurant_warehouse()$ WarehouseModel
        +create_workshop_warehouse()$ WarehouseModel
    }

    class SettingsModel {
        +organization: OrganizationModel
        +boss_name: str
        +account_name: str
        +is_first_start: bool
        +response_format: ResponseFormat
    }

    class OrganizationModel {
        +BIC_LENGTH = 9
        +ACCOUNT_LENGTH = 20
        +inn: str
        +bic: str
        +account: str
        +ownership_form: OwnershipForm
    }

    class TransactionModel {
        +nomenclature: NomenclatureModel
        +warehouse: WarehouseModel
        +range: RangeModel
        +quantity: int | float
        +period: datetime
    }

    class OwnershipForm {
        <<enumeration>>
        LLC
        JSC
        PJSC
        SOLE_PROPRIETOR
    }

    class ResponseFormat {
        <<enumeration>>
    }

    AbstractModel <|-- BaseEntity
    AbstractModel <|-- IngredientModel
    BaseEntity <|-- NamedEntity
    BaseEntity <|-- SettingsModel
    NamedEntity <|-- RangeModel
    NamedEntity <|-- NomenclatureModel
    NamedEntity <|-- NomenclatureGroupModel
    NamedEntity <|-- WarehouseModel
    NamedEntity <|-- OrganizationModel
    NamedEntity <|-- RecipeModel
    BaseEntity <|-- TransactionModel

    NomenclatureModel --> NomenclatureGroupModel : group
    NomenclatureModel --> RangeModel : range
    NomenclatureModel --> NomenclatureType : type
    IngredientModel --> NomenclatureModel : nomenclature
    IngredientModel "1" *-- "0..*" IngredientModel : base
    RecipeModel --> NomenclatureModel : result
    RecipeModel "1" *-- "*" IngredientModel : items
    RecipeModel ..> IngredientModel : as_ingredient
    NomenclatureCatalog o-- NomenclatureModel : items
    RecipeModel ..> NomenclatureCatalog : фабрики карт
    RangeModel --> RangeModel : base
    OrganizationModel --> OwnershipForm : ownership_form
    SettingsModel --> OrganizationModel : organization
    SettingsModel --> ResponseFormat : response_format
    TransactionModel --> NomenclatureModel : nomenclature
    TransactionModel --> WarehouseModel : warehouse
    TransactionModel --> RangeModel : range
```

`TransactionModel` — запись журнала складских операций. Наименования у неё нет, поэтому она наследует
`BaseEntity`. Знак `quantity` различает приход (+) и расход (−), ноль запрещён. Сеттеров нет: проведённая
запись не меняется. Единица записи — как в первичном документе («2 кг»), но её базовая единица должна совпадать
с базовой единицей номенклатуры (`range.base is nomenclature.range.base`), иначе `ArgumentsException`.

## Рецепты

Модели технологических карт (п. 2.1 и 2.5 ТЗ) и то, как они связаны с номенклатурой и хранилищем.
Те же классы показаны на общей диаграмме выше, здесь оставлено только относящееся к рецептам.

- Карта (`RecipeModel`) получает одну номенклатуру-результат: полуфабрикат или блюдо.
- Состав — ингредиенты `IngredientModel` без собственного `id`: внутри карты строку определяет номенклатура.
  Строка хранит количество в базовой единице номенклатуры, долю потерь и основание `base` — состав этого количества.
  «Компоновщик» в одном классе: пустое `base` — сырьё или упаковка, непустое — полуфабрикат или блюдо со своей картой.
- Вес сырья: брутто = `quantity * grams_per_base_unit`, нетто = брутто * (1 − `loss_ratio`).
- Вес составной строки: брутто = сумма брутто `base`, нетто = сумма нетто `base` * (1 − `loss_ratio`).
  Вес карты — сумма по строкам, вычисляется при каждом обращении.
- Полуфабрикат входит в карту снимком: `recipe.as_ingredient(quantity, loss_ratio)` копирует состав карты,
  масштабированный на `quantity / output_quantity`. Основание — производные данные, источник истины — карта
  полуфабриката (`StorageManager.find_recipe()` по номенклатуре строки). Правка карты уже собранные строки не меняет,
  каскадную пересборку в будущем возьмёт на себя наблюдатель. Ингредиент о картах не знает, цикла импортов нет.
- Циклы по ссылкам невозможны: `base` задаётся в конструкторе и копируется. `RecipeModel.add_item` отвергает строку,
  в дереве которой есть результат карты (`IngredientModel.contains`). Проверка надёжна, пока снимки свежие:
  устаревший снимок может не увидеть цепочку, добавленную после его сборки.
- Фабрики `create_*` собирают карты из `Recipes.md` по справочнику `NomenclatureCatalog` (поиск номенклатуры по наименованию).

```mermaid
classDiagram
    direction LR

    class NomenclatureType {
        <<enumeration>>
        RAW_MATERIAL
        PRODUCT
        SEMI_FINISHED
        DISH
        PACKAGING
    }

    class NomenclatureModel {
        +type: NomenclatureType
        +grams_per_base_unit: int | float
    }

    class IngredientModel {
        +nomenclature: NomenclatureModel
        +quantity: int | float
        +loss_ratio: int | float
        +base: tuple~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +scaled(factor) IngredientModel
        +contains(nomenclature) bool
        +nomenclature_key() UUID
    }

    note for IngredientModel "Строка состава, без id. loss_ratio от 0 включительно до 1 не включая. Пустое base — сырьё, непустое — снимок карты полуфабриката. contains нужен карте, чтобы не включить снимок самой себя"

    class NomenclatureCatalog {
        +get(name) NomenclatureModel
    }

    note for NomenclatureCatalog "Справочник номенклатуры: поиск по наименованию. Не владеет позициями, возвращает те же экземпляры. Повтор наименования отвергается"

    class RecipeModel {
        +RESULT_TYPES: frozenset~NomenclatureType~
        +result: NomenclatureModel
        +output_quantity: int | float
        +cooking_time_minutes: int | float
        +steps: list~str~
        +items: list~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +gross_weight_for(output_quantity) float
        +net_weight_for(output_quantity) float
        +add_item(item) None
        +remove_item(nomenclature) None
        +as_ingredient(quantity, loss_ratio) IngredientModel
        +result_key() UUID
        +create_beef_bouillon(catalog)$ RecipeModel
        +create_boiled_beef(catalog)$ RecipeModel
        +create_beet_fry(catalog)$ RecipeModel
        +create_borscht(catalog, bouillon?, boiled_beef?, beet_fry?)$ RecipeModel
    }

    note for RecipeModel "Результат — только SEMI_FINISHED или DISH, задаётся в конструкторе. Брутто и нетто — сумма по элементам. gross_weight_for и net_weight_for масштабируют веса под заданный объём. Результат не может входить в состав своей карты, в том числе в основание строки. as_ingredient масштабирует состав под количество строки"

    class UniqueCollection~T~ {
        +add(item) None
        +remove(key) None
        +key_of(item) Hashable
        +has_key(key) bool
    }

    note for UniqueCollection "Функцию ключа даёт сама модель: IngredientModel.nomenclature_key (id номенклатуры), RecipeModel.result_key (id результата), NamedEntity.name_key (наименование)"

    class StorageManager {
        +recipes: list~RecipeModel~
        +find_recipe(nomenclature) RecipeModel | None
        +find_recipe_by_name(name) RecipeModel | None
        +find(entity_type, entity_id) NamedEntity | None
        +entities(entity_type) list~NamedEntity~
        +find_referrers(target_id) list~BaseEntity~
        +entity_class(entity_type) type~NamedEntity~
        +all_entities() list~NamedEntity~
        +add(entity_type, entity) None
        +remove(entity_type, entity) None
        +replace(entity_type, entity, state) None
    }

    note for StorageManager "Одна карта на номенклатуру-результат. Включение снимка самой себя отвергает карта при добавлении строки, хранилище его не проверяет"

    class ArgumentsException

    NomenclatureModel --> NomenclatureType : type
    IngredientModel --> NomenclatureModel : nomenclature
    IngredientModel "1" *-- "0..*" IngredientModel : base
    RecipeModel --> NomenclatureModel : result
    RecipeModel "1" *-- "*" IngredientModel : items
    RecipeModel ..> IngredientModel : as_ingredient
    NomenclatureCatalog o-- NomenclatureModel : items
    RecipeModel ..> NomenclatureCatalog : фабрики карт
    RecipeModel *-- UniqueCollection : items
    StorageManager *-- UniqueCollection : recipes
    StorageManager --> RecipeModel : recipes
    StorageManager --> TransactionModel : transactions
    RecipeModel ..> ArgumentsException : нет номенклатуры в справочнике, дубликат, результат в составе или в основании строки
    StorageManager ..> ArgumentsException : вторая карта на результат
```

Пример составной карты: «Борщ с говядиной» (блюдо) включает полуфабрикаты «Бульон костный говяжий»,
«Говядина отварная», «Зажарка свекольная» и упаковку «Контейнер для супа 500 мл». Каждый полуфабрикат входит
снимком своей карты (`as_ingredient`) с количеством и потерями строки, а карты полуфабрикатов состоят только из сырья,
поэтому циклов в начальных данных нет.

## Проверки и ошибки

Все проверки бросают `ArgumentsException`. Модели вызывают валидаторы из сеттеров.
`OperationException` бросают менеджеры, когда операция не удалась при корректных аргументах
(файл недоступен, настройки не загружены), см. раздел «Менеджеры».

```mermaid
classDiagram
    direction LR

    class CommonValidator {
        +validate_string(value, field, max_length)$ str
        +validate_positive_number(value, field)$ int | float
        +validate_finite_number(value, field)$ int | float
        +validate_nonzero_number(value, field)$ int | float
        +validate_non_negative_number(value, field)$ int | float
        +validate_date(value, field)$ date
        +validate_datetime(value, field)$ datetime
        +validate_fraction(value, field)$ int | float
        +validate_digits(value, field, lengths)$ str
        +validate_instance(value, expected_type, field, message)$ T
        +validate_callable(value, field, message)$ T
        +validate_dict(value, field)$ dict~str, object~
        +validate_enum(value, enum_type, field)$ E
        +validate_field(data, key)$ object
    }

    class InnValidator {
        +LENGTHS: tuple~int~
        +validate(value, field)$ str
    }

    class ProjectException {
        <<abstract>>
        -_message: str
        -_stack_trace: str
        #_title()* str
    }

    class ArgumentsException {
        -_field: str
    }

    class OperationException

    class ReferencedEntityException {
        -_target_id: UUID
        -_referrers: tuple~str~
        +target_id: UUID
        +referrers: tuple~str~
    }

    note for ReferencedEntityException "На сущность есть ссылки, удалять её или менять код нельзя (п. 3 домашнего задания). Описания ссылающихся сущностей — строки, чтобы исключения не зависели от моделей. Бросает EntityService в delete, put и patch по результату StorageManager.find_referrers()"

    class Exception {
        <<built-in>>
    }

    class NamedEntity {
        <<abstract>>
    }

    class BaseEntity {
        <<abstract>>
    }

    class RangeModel
    class NomenclatureModel
    class IngredientModel
    class NomenclatureCatalog
    class RecipeModel
    class OrganizationModel
    class SettingsModel

    Exception <|-- ProjectException
    ProjectException <|-- ArgumentsException
    ProjectException <|-- OperationException
    ProjectException <|-- ReferencedEntityException
    InnValidator ..> CommonValidator : формат и цифры
    CommonValidator ..> ArgumentsException : бросает
    InnValidator ..> ArgumentsException : бросает
    BaseEntity ..> ArgumentsException : id
    NamedEntity ..> CommonValidator : name
    RangeModel ..> CommonValidator : factor, base
    NomenclatureModel ..> CommonValidator : name, full_name, group, range, type, grams_per_base_unit
    IngredientModel ..> CommonValidator : nomenclature, quantity, loss_ratio, base, factor
    IngredientModel ..> ArgumentsException : повтор номенклатуры в основании, своя номенклатура в основании
    NomenclatureCatalog ..> CommonValidator : nomenclatures
    NomenclatureCatalog ..> ArgumentsException : повтор наименования, нет позиции
    RecipeModel ..> CommonValidator : result, output_quantity, cooking_time_minutes, steps, item, nomenclature, quantity
    RecipeModel ..> ArgumentsException : тип результата, шаги, результат в составе или в основании строки
    OrganizationModel ..> CommonValidator : bic, account, ownership_form
    OrganizationModel ..> InnValidator : inn
    SettingsModel ..> CommonValidator : organization, boss_name, account_name, is_first_start
```

## Менеджеры

Менеджеры лежат в `Src/Logics/`, базовые классы и `UniqueCollection` — в `Src/Core/`.
`AbstractManager` задаёт только общий контракт: флаг `is_loaded` и абстрактный `load()`.
`AbstractFileManager` добавляет работу с файлами: базовый `load(file_name)` сначала вызывает `_read()`,
затем `convert()`. Наследники реализуют `_read()` и `convert()`, но не переопределяют `load()`.
Менеджер без файлов (`StorageManager`) наследует `AbstractManager` напрямую и реализует `load()` сам.
Менеджер — Singleton: каждый конкретный класс реализует это в своём `__new__` и хранит экземпляр
в собственном `_instance`. Базовые классы Singleton не реализуют.
Пунктирная стрелка — зависимость (использует или бросает), стрелка с ромбом — владение.

### SettingsManager

Читает `settings.json` и собирает из него `SettingsModel` общим механизмом десериализации — `DeserializerFactory`,
тем же, что загружает хранилище из файла. Модели создают себя сами (`from_dict`), поэтому правила полей
(обязательные, значения по умолчанию, перечисления) описаны один раз, в моделях. В файле настроек, который правит
человек, нет служебного `model_type`: его подставляет `_typed()` для корня и карточки организации, а уже указанный
тип не заменяет. Ошибки модели (`ArgumentsException`) превращает в `OperationException`, чтобы вызывающий код
ловил одно исключение.

```mermaid
classDiagram
    direction TB

    class AbstractManager {
        <<abstract>>
        -_is_loaded: bool
        +is_loaded: bool
        +load()* None
        #_initialize() None
    }

    class AbstractFileManager {
        <<abstract>>
        -_data: dict~str, Any~
        +load(file_name) None
        #_initialize() None
        #_read(file_name)* dict
        +convert()* None
    }

    note for AbstractFileManager "load() задаёт порядок: _read(), затем convert(). is_loaded становится True только после успеха"

    class Common {
        -_ROOT_MARKER$: str
        +find_project_root(start)$ Path
        +resolve_path(file_name, default_name)$ Path
        +get_fields(source, exclude)$ list~str~
    }

    note for Common "Корень проекта ищется вверх от расположения модуля по pyproject.toml, а не от текущего каталога. get_fields работает с классом: геттеры не вызываются"

    class SettingsManager {
        -_instance$: SettingsManager | None
        -_default_file_name: str
        -_settings: SettingsModel | None
        +settings: SettingsModel
        +__new__() Self
        #_initialize() None
        -_default_data()$ dict
        #_read(file_name) dict
        -_read_file(path)$ dict
        -_write_defaults(path) None
        -_typed(data)$ dict
        +convert() None
    }

    note for SettingsManager "Singleton: __new__ создаёт экземпляр один раз и вызывает _initialize(). Файл по умолчанию settings.json в корне проекта. Если файл не читается, берутся настройки по умолчанию, отсутствующий файл создаётся. Модель присваивается только целиком, при ошибке прежние настройки не затираются"

    class SettingsModel {
        +organization: OrganizationModel
        +boss_name: str
        +account_name: str
        +is_first_start: bool
        +response_format: ResponseFormat
    }

    class OrganizationModel
    class OwnershipForm {
        <<enumeration>>
    }
    class ResponseFormat {
        <<enumeration>>
    }
    class DeserializerFactory {
        +deserialize_as(target_type, data) T
    }
    class ArgumentsException
    class OperationException

    AbstractManager <|-- AbstractFileManager
    AbstractFileManager <|-- SettingsManager
    SettingsManager --> SettingsModel : settings
    SettingsModel --> OrganizationModel : organization
    OrganizationModel --> OwnershipForm : ownership_form
    SettingsModel --> ResponseFormat : response_format
    SettingsManager ..> Common : путь к файлу
    Common ..> OperationException : бросает
    SettingsManager ..> DeserializerFactory : convert() собирает SettingsModel
    SettingsManager ..> OrganizationModel : model_type в _typed()
    SettingsManager ..> ArgumentsException : перехватывает
    SettingsManager ..> OperationException : бросает
```

### StorageManager

Хранит доменные модели в пяти коллекциях без дубликатов. При первом запуске (`is_first_start` в настройках)
`load()` наполняет их начальными данными через фабричные методы моделей: 5 единиц измерения, 7 групп,
24 номенклатуры, 2 склада и 4 технологические карты из `Recipes.md`.
Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях, а карты — на те же объекты номенклатуры, а не на копии.
Циклы включений хранилище не проверяет: снимок самой себя отвергает карта при добавлении строки (`RecipeModel.add_item`).
Карту полуфабриката находит `find_recipe()` по номенклатуре-результату, на одну позицию допускается одна карта.
По наименованию карту ищет `find_recipe_by_name()` (без учёта регистра), её использует API отчёта.
Сущность по типу (`EntityType`: номенклатура, группа номенклатуры, единица измерения, склад, карта) и коду ищет `find()` перебором коллекции этого типа,
все сущности типа возвращает `entities()` (копия списка): по ним API отдаёт коллекцию.
Сущности, ссылающиеся на сущность с заданным кодом, возвращает `find_referrers()`: он берёт ответ из обратного индекса `_referrers` (код цели → ссылающиеся сущности) за одно обращение к словарю и отдаёт копию списка. Это основа запрета удаления связанных сущностей.
Прямые ссылки сущности находит `ReferenceScanner` (`Src/Logics/reference_scanner.py`): он сам обходит состояние модели (`vars`), коллекции, словари и вложенные `AbstractModel`, останавливаясь на встреченных `BaseEntity` и пропуская ссылку на саму сущность. Индекс ведут `add`, `remove` и `replace` через `_index_references()` и `_unindex_references()`; `replace` вычёркивает старые ссылки до `replace_state` и записывает новые после.
Повторы ссылок (сырьё в строке карты и в основании полуфабриката) записываются один раз. Значения индекса — списки, а не множества:
хэш сущности считается по `id`, а `replace` может сменить код ссылающейся сущности. Поэтому начальные данные
и данные из файла тоже добавляются через `add()`, а `_reset_collections()` очищает индекс вместе с коллекциями.
Состав хранилища описан одной таблицей `_KINDS: dict[EntityType, _EntityKind]`: для каждого типа — класс модели,
функция ключа коллекции и ключ в файле выгрузки. Из неё `_reset_collections()` строит коллекции (`_entities`),
`entity_class()` берёт класс для проверки, `_collections()` — ключи файла. Новый тип сущности подключается
значением в `EntityType`, строкой в `_KINDS` и свойством для выгрузки (`ranges` и т. п.); тест сверяет `_KINDS`
с `EntityType` и ключи файла со свойствами. Таблица лежит в хранилище, а не в моделях или `Src/Core`:
модели не должны знать, как их хранят, а ядро — зависеть от моделей.
Хранилище только хранит и отдаёт сущности. Меняют коллекции `add`, `remove` и `replace`, они следят лишь за целостностью
самих коллекций: класс сущности соответствует типу (`entity_class()`), ключ не повторяется, удаляемая сущность есть.
`replace` переносит состояние на месте (`BaseEntity.replace_state`) и перекладывает сущность под новый ключ, если
наименование изменилось. Сценарии создания, изменения и удаления с бизнес-правилами выполняет `EntityService` (ниже).
Хранилище зависит от менеджера настроек: `load(settings_manager)` принимает его параметром, по умолчанию берёт
единственный `SettingsManager`. Настройки должны быть загружены до `StorageManager.load()`, сам `load()` их не загружает.
Если в `load(file_name=...)` указан файл, коллекции читаются из него, а настройки не нужны и флаг первого запуска
не учитывается. Файл — выгрузка хранилища через `ConverterFactory` (ключи `ranges`, `nomenclature_groups`,
`nomenclatures`, `warehouses`, `recipes`). `_collections()` выводит из `_KINDS` пары «ключ коллекции
→ тип сущностей» (`EntityType`); модели добавляются через `add()`, который проверяет класс модели и пишет ссылки в индекс. Загрузка идёт циклом по ключам файла
в их порядке, лишние ключи (`is_loaded`) пропускаются, отсутствующая коллекция — ошибка. Какую модель собирать,
говорит сам файл (`model_type`). Все коллекции загружаются в одной сессии `DeserializerFactory`, поэтому
единицы, группы и номенклатура становятся общими объектами, а не копиями, и `find_recipe()` их находит.
Порядок коллекций в файле на результат не влияет: модели записаны целиком, общие объекты сводит кэш по `id`.
Журнал складских операций (`TransactionModel`) хранится отдельно от `_KINDS`, в списке `_transactions`: журнал
только дописывается (`add_transaction`), а общий CRUD с PUT и DELETE противоречит доменной модели. Свойство
`transactions` отдаёт копию списка в порядке проведения. Записи журнала попадают в обратный индекс ссылок,
поэтому номенклатуру, склад и единицу из журнала удалить нельзя. При первом запуске создаются 9 записей
за сентябрь — ноябрь 2026. В файле выгрузки ключ `transactions` необязателен: старая выгрузка загружается
с пустым журналом.
`StorageManager` читает файл сам, а не через `AbstractFileManager`: у того `load(file_name)` и жёсткая схема
`_read` + `convert`, а хранилищу нужен ещё и параметр `settings_manager`, поэтому наследует `AbstractManager`.

```mermaid
classDiagram
    direction TB

    class AbstractManager {
        <<abstract>>
        -_is_loaded: bool
        +is_loaded: bool
        +load()* None
        #_initialize() None
    }

    class StorageManager {
        -_instance$: StorageManager | None
        -_KINDS$: dict~EntityType, _EntityKind~
        -_entities: dict~EntityType, UniqueCollection~NamedEntity~~
        -_referrers: dict~UUID, list~BaseEntity~~
        -_scanner: ReferenceScanner
        -_transactions: list~TransactionModel~
        +ranges: list~RangeModel~
        +nomenclature_groups: list~NomenclatureGroupModel~
        +nomenclatures: list~NomenclatureModel~
        +warehouses: list~WarehouseModel~
        +recipes: list~RecipeModel~
        +transactions: list~TransactionModel~
        +__new__() Self
        +load(settings_manager, file_name) None
        +find_recipe(nomenclature) RecipeModel | None
        +find_recipe_by_name(name) RecipeModel | None
        +find(entity_type, entity_id) NamedEntity | None
        +entities(entity_type) list~NamedEntity~
        +find_referrers(target_id) list~BaseEntity~
        +entity_class(entity_type) type~NamedEntity~
        +all_entities() list~NamedEntity~
        +add(entity_type, entity) None
        +remove(entity_type, entity) None
        +replace(entity_type, entity, state) None
        +add_transaction(transaction) None
        #_initialize() None
        -_reset_collections() None
        -_fill_first_start_data() None
        -_load_from_file(file_name) None
        -_collections() dict~str, EntityType~
        -_read_file(path)$ dict
        -_load_collection(factory, key, items, entity_type) None
        -_create_nomenclatures() list~NomenclatureModel~
        -_index_references(entity) None
        -_unindex_references(entity) None
        -_validate_entity(entity_type, entity) NamedEntity
    }

    class _EntityKind {
        <<dataclass frozen>>
        +model_class: type~NamedEntity~
        +key_func: Callable~NamedEntity, Hashable~
        +file_key: str
    }

    note for _EntityKind "Описание типа сущности хранилища. Таблица StorageManager._KINDS — единственное место, где перечислены коллекции: по ней строятся коллекции, проверяется класс сущности и сопоставляются ключи файла"

    note for StorageManager "Singleton: __new__ создаёт экземпляр один раз и вызывает _initialize(). Свойства возвращают копии списков. load() каждый раз пересоздаёт коллекции. Ключ коллекции карт — id результата"

    class UniqueCollection~T~ {
        -_key: Callable~T, Hashable~
        -_items: dict~Hashable, T~
        +add(item) None
        +remove(key) None
        +key_of(item) Hashable
        +has_key(key) bool
    }

    note for UniqueCollection "Ключ уникальности задаёт функция, которую даёт модель: NamedEntity.name_key (наименование без учёта регистра), IngredientModel.nomenclature_key (id номенклатуры), RecipeModel.result_key (id результата). add принимает элемент, remove — ключ. Поддерживает итерацию и len()"

    class SettingsManager {
        +settings: SettingsModel
    }

    class RangeModel {
        +base: RangeModel
        +factor: int | float
    }

    class NomenclatureModel {
        +group: NomenclatureGroupModel
        +range: RangeModel
    }

    class NomenclatureGroupModel
    class WarehouseModel
    class RecipeModel
    class TransactionModel
    class NomenclatureCatalog
    class DeserializerFactory
    class ReferenceScanner {
        +scan(source) list~BaseEntity~
        -_walk(value, root, visited, seen_references, references) None
        -_field_values(model)$ Iterable~object~
    }
    class ArgumentsException
    class OperationException

    AbstractManager <|-- StorageManager
    StorageManager "1" *-- "5" UniqueCollection : коллекции
    StorageManager *-- ReferenceScanner : _scanner
    StorageManager --> _EntityKind : _KINDS
    StorageManager ..> SettingsManager : зависимость, параметр load(), читает is_first_start
    StorageManager --> RangeModel : ranges
    StorageManager --> NomenclatureGroupModel : nomenclature_groups
    StorageManager --> NomenclatureModel : nomenclatures
    StorageManager --> WarehouseModel : warehouses
    StorageManager --> RecipeModel : recipes
    StorageManager ..> NomenclatureCatalog : при первом старте строит и передаёт в фабрики карт
    StorageManager ..> DeserializerFactory : load(file_name) загружает коллекции в одной сессии
    NomenclatureModel --> NomenclatureGroupModel : group
    NomenclatureModel --> RangeModel : range
    RangeModel --> RangeModel : base
    UniqueCollection ..> ArgumentsException : бросает при дубликате и удалении отсутствующего ключа
    StorageManager ..> OperationException : бросает
```

### EntityService

Сервис доменных сущностей (паттерн Service Layer, `Src/Logics/entity_service.py`): сценарии `create`, `put`,
`patch` и `delete`, которые вызывают CRUD-маршруты API `/api/entities/...`. Сервис решает, можно ли выполнить
операцию, а хранилище только исполняет: сервис обращается к нему через публичные методы и не трогает коллекции.
Хранилище сервис получает в конструкторе, по умолчанию берёт единственный `StorageManager`.
Данные — словарь в формате выгрузки, вложенные сущности хранилища задаются ссылкой `{"id": ...}`, `model_type`
необязателен. `put` заменяет все поля, `patch` накладывает указанные на текущие (выгрузка сущности + данные).
Сущность собирается в стороне через `DeserializerFactory.session(known)`, где известны все сущности хранилища,
и проверяется до первого изменения: ссылки должны вести на сущности хранилища, код — быть свободным во всём
хранилище. Удалить сущность или сменить ей код, пока на неё ссылаются (`StorageManager.find_referrers()`), нельзя:
`ReferencedEntityException`. Остальные поля у связанной сущности менять можно. Каскадной пересборки снимков карт
при правке сущностей пока нет.

```mermaid
classDiagram
    direction LR

    class EntityService {
        -_storage: StorageManager
        -_scanner: ReferenceScanner
        +__init__(storage, scanner)
        +create(entity_type, data) NamedEntity
        +put(entity_type, entity_id, data) NamedEntity
        +patch(entity_type, entity_id, data) NamedEntity
        +delete(entity_type, entity_id) None
        -_get(entity_type, entity_id) NamedEntity
        -_update(entity_type, entity_id, data, merge) NamedEntity
        -_build_entity(entity_type, data, exclude) NamedEntity
        -_ensure_id_is_free(entity) None
        -_ensure_not_referenced(entity) None
        -_describe(entity) str
    }

    class ReferenceScanner {
        +scan(source) list~BaseEntity~
    }

    class StorageManager {
        +find(entity_type, entity_id) NamedEntity | None
        +entities(entity_type) list~NamedEntity~
        +find_referrers(target_id) list~BaseEntity~
        +entity_class(entity_type) type~NamedEntity~
        +all_entities() list~NamedEntity~
        +add(entity_type, entity) None
        +remove(entity_type, entity) None
        +replace(entity_type, entity, state) None
    }

    class DeserializerFactory
    class ConverterFactory
    class ArgumentsException
    class ReferencedEntityException

    EntityService --> StorageManager : публичные методы
    EntityService --> ReferenceScanner : проверка ссылок новой сущности
    EntityService ..> DeserializerFactory : собирает сущность из данных
    EntityService ..> ConverterFactory : patch — текущие поля
    EntityService ..> ArgumentsException : некорректные данные, занятый код
    EntityService ..> ReferencedEntityException : delete, смена кода
```

## Отчёты

Отчёт формирует по сущности результат в одном из форматов (`ResponseFormat`). У каждого формата свой класс отчёта
со своей реализацией `build()` и своими признаками выдачи (`is_binary`, `media_type`, `file_extension`).
Клиент получает отчёт от фабрики по формату и работает только с абстракцией `AbstractReport`
(паттерн «Абстрактная фабрика»). Абстракции лежат в `Src/Core/`, отчёты и фабрика — в `Src/Logics/`,
результат `ReportResult` — в `Src/Dtos/`.

Фабрика хранит настройки (`SettingsModel`): `create(response_format)` создаёт отчёт явно указанного формата,
`create_default()` — формата из `SettingsModel.response_format`. Новый формат подключается строкой в `_reports`.

Общие для всех форматов правила обхода заданы в `AbstractReport`: поля — публичные свойства (`Common.get_fields`),
вложенная сущность с наименованием выводится ссылкой (наименование и код), списки — поэлементно,
остальные объекты раскрываются по дереву «Компоновщика» (`RecipeModel.items`, `IngredientModel.base`).
Так не зацикливается `RangeModel.base` у базовой единицы, а все форматы выводят один и тот же состав данных.

Результат — объект-значение: без идентификатора, неизменяем, равенство по содержимому и способу выдачи.
Он один на все форматы: формат знает про себя отчёт и передаёт результату MIME-тип, расширение и признак
файла (`AbstractReport._result()`). `is_binary` подсказывает API, отдавать ли результат файлом на скачивание
(Markdown, CSV) или текстом (TXT, XML, HTML). Сам результат собирает HTTP-ответ (`to_response()`), поэтому
`fastapi` нужен только в `Src/Dtos/` и `Src/main.py`, а не в ядре. CSV кодируется с меткой UTF-8 для Excel
(`CsvReport._ENCODING`). Компромисс: `AbstractReport` из `Src/Core/` импортирует `ReportResult` из `Src/Dtos/`.

```mermaid
classDiagram
    direction TB

    class AbstractReportFactory {
        <<abstract>>
        +create(response_format)* AbstractReport
        +create_default()* AbstractReport
    }

    class ReportFactory {
        -_reports$: dict~ResponseFormat, type~
        -_settings: SettingsModel
        +settings: SettingsModel
        +create(response_format) AbstractReport
        +create_default() AbstractReport
    }

    class AbstractReport {
        <<abstract>>
        #_FLOAT_PRECISION: int
        #_ENCODING$: str
        +is_binary*: bool
        +media_type*: str
        +file_extension*: str
        +build(source)* ReportResult
        #_result(text) ReportResult
        #_fields(source)$ list~tuple~
        #_is_scalar(value)$ bool
        #_is_reference(value)$ bool
        #_is_collection(value)$ bool
        #_format_reference(entity)$ str
        #_format_scalar(value)$ str
    }

    class TxtReport {
        +is_binary = False
        +media_type = text/plain
        +file_extension = txt
        +build(source) ReportResult
    }

    class MarkdownReport {
        +is_binary = True
        +media_type = text/markdown
        +file_extension = md
        +build(source) ReportResult
    }

    class CsvReport {
        #_ENCODING$ = utf-8-sig
        +is_binary = True
        +media_type = text/csv
        +file_extension = csv
        +build(source) ReportResult
    }

    class XmlReport {
        +is_binary = False
        +media_type = application/xml
        +file_extension = xml
        +build(source) ReportResult
    }

    class HtmlReport {
        +is_binary = False
        +media_type = text/html
        +file_extension = html
        +build(source) ReportResult
    }

    class ReportResult {
        -_text: str
        -_encoding: str
        +text: str
        +binary: bytes
        +is_binary: bool
        +media_type: str
        +file_extension: str
        +to_response(file_stem) Response
        +__eq__(value) bool
        +__hash__() int
    }

    class ResponseFormat {
        <<enumeration>>
        TXT
        MARKDOWN
        CSV
        XML
        HTML
    }

    class SettingsModel {
        +response_format: ResponseFormat
    }

    class NamedEntity
    class Common
    class ArgumentsException

    AbstractReportFactory <|-- ReportFactory
    AbstractReport <|-- TxtReport
    AbstractReport <|-- MarkdownReport
    AbstractReport <|-- CsvReport
    AbstractReport <|-- XmlReport
    AbstractReport <|-- HtmlReport
    AbstractReportFactory ..> AbstractReport : создаёт
    ReportFactory --> SettingsModel : settings
    SettingsModel --> ResponseFormat : response_format
    ReportFactory ..> ResponseFormat : ключ сопоставления
    AbstractReport ..> ReportResult : возвращает
    AbstractReport ..> NamedEntity : строит по сущности
    AbstractReport ..> Common : get_fields
    ReportFactory ..> ArgumentsException : бросает для чужого или нереализованного формата
```

## Конвертация

Конвертеры превращают любой объект в данные, которые `json.dumps` записывает без настроек: модель — словарь
«наименование поля — данные поля», список моделей — список словарей, простое значение — само значение.
Это основа сериализации: модель или всё хранилище сначала становится словарём, а словарь — JSON.
Абстракция лежит в `Src/Core/`, конвертеры и фабрика — в `Src/Logics/`.

Клиент вызывает только `ConverterFactory.convert(source)`, где `source` — объект любого типа. Фабрика выбирает
конвертер по типу значения (`create()`) по сопоставлению `_converters` с обходом MRO типа, без цепочки `isinstance`:

| Тип значения                                   | Конвертер             | Данные                                  |
|------------------------------------------------|-----------------------|-----------------------------------------|
| `str`, `int`, `float`, `bool`, `None`          | `BasicConverter`      | как есть                                |
| `Enum`, `UUID`                                 | `BasicConverter`      | значение перечисления, строка кода      |
| `date`, `datetime`                             | `DatetimeConverter`   | строка ISO 8601                         |
| `list`, `tuple`                                | `CollectionConverter` | список данных элементов                 |
| `dict` со строковыми ключами                   | `DictConverter`       | словарь данных значений                 |
| остальные объекты (`object`): модели и т. п.   | `ReferenceConverter`  | вложенный словарь полей                 |

Конвертер возвращает `{поле: данные}`, а у значения верхнего уровня поля нет. Поэтому `convert` передаёт
служебное наименование `_ROOT_FIELD` и сразу снимает его с результата.

Рекурсия: `ReferenceConverter` раскрывает объект через `ConverterFactory._fields`, а тот для каждого поля
(`Common.get_fields`) снова выбирает конвертер. `CollectionConverter` и `DictConverter` отдают каждый элемент
в `ConverterFactory.convert`. Фабрика передаёт конвертерам свои методы функциями, поэтому конвертеры
не зависят от её класса и цикла импортов нет.

```mermaid
sequenceDiagram
    participant Client as Клиент
    participant F as ConverterFactory
    participant R as ReferenceConverter
    participant C as CollectionConverter / DictConverter
    participant B as BasicConverter

    Client->>F: convert(storage)
    F->>F: create(storage)
    F->>R: convert(_ROOT_FIELD, storage)
    R->>F: _fields(storage), через функцию
    loop каждое поле объекта
        F->>F: create(value)
        alt простое значение
            F->>B: convert(field, value)
        else список или словарь
            F->>C: convert(field, value)
            C->>F: convert(item) для каждого элемента — рекурсия
        else вложенная модель
            F->>R: convert(field, value)
            R->>F: _fields(value), через функцию — рекурсия
        end
    end
    F-->>Client: данные для JSON
```

Защита от циклов: фабрика помнит путь от корня до текущего объекта. Объект, который уже есть на пути
(у базовой единицы `RangeModel.base` — она сама), записывается ссылкой `{"id": ...}`. Цикл через объект
без идентификатора — `OperationException`. Общая модель без цикла (одна группа у разных позиций) раскрывается
везде целиком. Поля — все публичные свойства, поэтому вычисляемые (`is_base`, веса) тоже попадают в словарь.
Объект без публичных свойств (функция, множество) — `ArgumentsException`: пустой словарь молча потерял бы данные.

```mermaid
classDiagram
    direction TB

    class AbstractConverter {
        <<abstract>>
        +convert(field, value)* dict~str, object~
        #_entry(field, data)$ dict~str, object~
    }

    class BasicConverter {
        +convert(field, value) dict~str, object~
    }

    class DatetimeConverter {
        +convert(field, value) dict~str, object~
    }

    class ReferenceConverter {
        -_expand: Callable
        +convert(field, value) dict~str, object~
    }

    class CollectionConverter {
        -_convert_item: Callable
        +convert(field, value) dict~str, object~
    }

    class DictConverter {
        -_convert_value: Callable
        +convert(field, value) dict~str, object~
    }

    class ConverterFactory {
        -_converters: dict~type, AbstractConverter~
        -_path: list~object~
        +create(value) AbstractConverter
        +convert(source) object
        -_fields(source) dict~str, object~
        -_cycle_reference(source) dict~str, object~
    }

    class Common
    class CommonValidator
    class BaseEntity {
        <<abstract>>
    }
    class ArgumentsException
    class OperationException

    AbstractConverter <|-- BasicConverter
    AbstractConverter <|-- DatetimeConverter
    AbstractConverter <|-- ReferenceConverter
    AbstractConverter <|-- CollectionConverter
    AbstractConverter <|-- DictConverter
    ConverterFactory *-- AbstractConverter : _converters
    ConverterFactory ..> AbstractConverter : create
    ReferenceConverter ..> ConverterFactory : _fields, функцией
    CollectionConverter ..> ConverterFactory : convert, функцией
    DictConverter ..> ConverterFactory : convert, функцией
    ConverterFactory ..> Common : get_fields
    ConverterFactory ..> BaseEntity : ссылка по id в цикле
    AbstractConverter ..> CommonValidator : наименование поля
    ReferenceConverter ..> CommonValidator : expand
    CollectionConverter ..> CommonValidator : convert_item
    DictConverter ..> CommonValidator : convert_value
    BasicConverter ..> ArgumentsException : не простое значение
    DatetimeConverter ..> ArgumentsException : не дата
    CollectionConverter ..> ArgumentsException : не список или кортеж, convert_item не функция
    DictConverter ..> ArgumentsException : не словарь, ключ не строка, convert_value не функция
    ReferenceConverter ..> ArgumentsException : expand не функция
    ConverterFactory ..> ArgumentsException : объект без публичных свойств
    ConverterFactory ..> OperationException : цикл без идентификатора
```

## Десериализация

Обратная сторона конвертации: данные из JSON превращаются обратно в модели. Абстракция лежит в `Src/Core/`,
десериализаторы и фабрика — в `Src/Logics/`. Как и конвертер, десериализатор выбирается по **виду значения**:
словарь — `ModelDeserializer`, список — `ListDeserializer`, строка, число, bool и None — `BasicDeserializer`.
Ни один десериализатор не знает конкретных моделей: какую модель собирать, записано в данных (`model_type`),
а создаёт модель её фабричный метод `AbstractModel.from_dict`. Новая модель подключается только своим `from_dict`.

`ModelDeserializer.deserialize`:

1. есть `id`, и модель уже в кэше — вернуть её: одному `id` соответствует один объект;
2. в словаре только `id` (ссылка): модель с этим `id` сейчас собирается выше по вложенности — это цикл,
   вернуть `None`; иначе — `OperationException` (ссылка на неизвестный объект). В домене цикл один:
   базовая единица ссылается сама на себя, и `RangeModel` понимает `base=None` как «я базовая»;
3. класс модели — по `model_type` из реестра `AbstractModel` (`resolve_type`), не импортом модуля по строке
   из файла. Нет `model_type` или тип неизвестен — `ArgumentsException`;
4. `id` попадает в множество собираемых, значения всех полей собираются рекурсивно через `_resolve`,
   модель создаёт `from_dict`, затем ей выставляется `id`, и она кладётся в кэш. Модели без `id`
   (ингредиент) в кэш не попадают.

Десериализаторы получают функцию `_resolve` фабрики, как конвертеры получают `ConverterFactory.convert`:
так сохраняется рекурсия и нет зависимости от класса фабрики. Кэш и множество собираемых принадлежат фабрике
и передаются `ModelDeserializer` общими объектами.

Клиент вызывает `DeserializerFactory.deserialize(data)` или `deserialize_as(target_type, data)`: второй
не выбирает модель, а только проверяет, что получен ожидаемый тип. Кэш живёт одну загрузку: `deserialize`
очищает его в `finally`. Поэтому фабрика хранит состояние и не годится для параллельных вызовов.
Когда данные состоят из нескольких частей (коллекции хранилища), а модели должны быть общими между ними,
части загружаются в одной сессии: `with factory.session(): ...`. Внутри сессии `deserialize` кэш не очищает,
очистка происходит при выходе из неё, в том числе после ошибки. Вложенная сессия — `OperationException`.

Модель в `from_dict` достаёт поля через `CommonValidator.validate_field` (обязательное поле, иначе
`ArgumentsException`), значение перечисления превращает `CommonValidator.validate_enum`. Типы значений
проверяют конструкторы моделей. Вычисляемые поля из файла (`is_base`, `gross_weight`, `net_weight`) игнорируются.

```mermaid
classDiagram
    direction TB

    class AbstractDeserializer {
        <<abstract>>
        +deserialize(data)* object
    }

    class ModelDeserializer {
        -_resolve: Callable
        -_cache: dict~UUID, BaseEntity~
        -_in_progress: set~UUID~
        +deserialize(data) object
        -_build(model_class, fields, entity_id) AbstractModel
        -_read_id(data)$ UUID | None
    }

    class ListDeserializer {
        -_resolve: Callable
        +deserialize(data) object
    }

    class BasicDeserializer {
        +deserialize(data) object
    }

    class DeserializerFactory {
        -_deserializers: dict~type, AbstractDeserializer~
        -_cache: dict~UUID, BaseEntity~
        -_in_progress: set~UUID~
        -_in_session: bool
        +session(known) Generator
        +create(data) AbstractDeserializer
        +deserialize(data) object
        +deserialize_as(target_type, data) T
        -_resolve(data) object
    }

    class AbstractModel {
        <<abstract>>
        +model_type: str
        +from_dict(data)* Self
        +resolve_type(model_type)$ type~AbstractModel~
    }
    class BaseEntity {
        <<abstract>>
    }
    class CommonValidator
    class ArgumentsException
    class OperationException

    AbstractDeserializer <|-- ModelDeserializer
    AbstractDeserializer <|-- ListDeserializer
    AbstractDeserializer <|-- BasicDeserializer

    DeserializerFactory *-- AbstractDeserializer : _deserializers
    ModelDeserializer ..> DeserializerFactory : _resolve, функцией
    ListDeserializer ..> DeserializerFactory : _resolve, функцией
    ModelDeserializer ..> AbstractModel : resolve_type, from_dict
    ModelDeserializer o-- BaseEntity : _cache
    DeserializerFactory o-- BaseEntity : _cache
    ModelDeserializer ..> CommonValidator : словарь, model_type, id у сущности
    ListDeserializer ..> CommonValidator : список
    DeserializerFactory ..> CommonValidator : deserialize_as
    ModelDeserializer ..> ArgumentsException : нет model_type, некорректный id
    ModelDeserializer ..> OperationException : ссылка на неизвестный объект
    DeserializerFactory ..> ArgumentsException : значение не из JSON, неверный тип
    DeserializerFactory ..> OperationException : вложенная сессия
```

## Фильтрация

Фильтр отбирает доменные модели любого типа по условиям из тела запроса (паттерн «Прототип»).
Условие (`FilterItemDto`) — путь к полю через точку (`field_name`), способ сравнения (`FilterType`: `EQUALS` —
полное совпадение, `LIKE` — вхождение строки) и значение. Набор условий (`FilterDto`) работает как логическое И,
пустой набор пропускает всё. Перечисление лежит в `Src/Core/`, DTO — в `Src/Dtos/`.

`AbstractPrototype` (`Src/Core/`) хранит копию списка данных и объявляет `clone(filter_dto)`. `Prototype` — один
на все модели: `clone` проверяет первое условие и рекурсивно клонирует новый прототип с остальными условиями.
Исходный прототип не меняется, копируется только список, модели остаются теми же объектами хранилища.
`_matches` знает способ сравнения: новое значение `FilterType` меняет только его, а `assert_never` заставляет
проверку типов указать на забытую ветку. Значения сравниваются строками, у перечисления — его значение
(`"сырьё"`), как в выгрузке.

`FieldPathReader` читает значения по пути (`range.base.name`, `items.nomenclature.name`). Шаг пути допустим, только
если это публичное свойство (`Common.get_fields`): новой модели ничего объявлять не нужно, а приватные поля
недоступны (`ArgumentsException`, API отвечает 400). Коллекция на пути шаг не тратит: остаток пути применяется
к каждому элементу, поэтому результат — список значений, и условие выполнено, если совпало хотя бы одно.

```mermaid
classDiagram
    direction LR

    class FilterType {
        <<enumeration>>
        EQUALS
        LIKE
    }

    class FilterItemDto {
        +field_name: str
        +filter_type: FilterType
        +value: str
        +from_dict(data)$ Self
    }

    class FilterDto {
        +filters: list~FilterItemDto~
        +from_dict(data)$ Self
    }

    class AbstractPrototype~T~ {
        <<abstract>>
        -_data: list~T~
        +data: list~T~
        +clone(filter_dto)* AbstractPrototype~T~
    }

    class Prototype~T~ {
        -_reader: FieldPathReader
        +clone(filter_dto) Prototype~T~
        -_matches(model, item) bool
        -_to_text(value)$ str
    }

    class FieldPathReader {
        +read(source, path) list~object~
        -_read_field(source, field) object
        -_walk(value, steps) list~object~
    }

    class Common {
        +get_fields(source)$ list~str~
    }

    class ArgumentsException

    FilterDto "1" *-- "*" FilterItemDto : filters
    FilterItemDto --> FilterType : filter_type
    AbstractPrototype <|-- Prototype
    AbstractPrototype ..> FilterDto : clone
    Prototype --> FieldPathReader : читает значения
    FieldPathReader ..> Common : публичные свойства
    FieldPathReader ..> ArgumentsException : недоступное поле
```

## Оборотно-сальдовая ведомость

ОСВ строит `TurnoverService` (`Src/Logics/`) по журналу хранилища. Запрос (`TurnoverRequestDto`) — период `start`
и `end` (обе границы включительно, `ГГГГ-ММ-ДД`) и условия `FilterDto` в том же теле. Записи журнала отбирает
`Prototype`, а период применяет сам сервис: записи до начала дают остаток на начало, поэтому Прототип их
не отбрасывает. Нет `end` — по сегодняшний день, нет `start` — с даты первой отобранной записи.

`_calculate_rows` группирует записи по паре «номенклатура + склад» с помощью типизированного ключа
`TurnoverGroupKeyDto` (строки в порядке первой записи группы), накапливает показатели в `TurnoverAccumulatorDto`,
пересчитывает количество в базовую единицу номенклатуры (`quantity × range.factor`) и раскладывает его по датам:
строго до `start` — начало, с `start` по `end` — приход или расход (модуль), после `end` — не учитывается.
Если единицу номенклатуры сменили после проведения записей и базы не совпадают, сервис бросает
`OperationException` (API отвечает 500).

Результат — объекты, а не словари: `TurnoverReport` хранит период и строки `TurnoverRow`, остаток на конец строка
вычисляет сама (`opening + income − outcome`). В JSON отчёт превращает `ConverterFactory`.

```mermaid
classDiagram
    direction LR

    class TurnoverRequestDto {
        +start: date | None
        +end: date | None
        +filter: FilterDto
        +from_dict(data)$ Self
    }

    class TurnoverGroupKeyDto {
        +nomenclature: NomenclatureModel
        +warehouse: WarehouseModel
        +__eq__(other) bool
        +__hash__() int
    }

    class TurnoverAccumulatorDto {
        +nomenclature: NomenclatureModel
        +warehouse: WarehouseModel
        +range: RangeModel
        +opening: float
        +income: float
        +outcome: float
        +record(transaction, start) void
        +to_row() TurnoverRow
    }

    class TurnoverService {
        -_storage: StorageManager
        +__init__(storage)
        +build(request) TurnoverReport
        -_calculate_rows(transactions, start, end) list~TurnoverRow~
    }

    class TurnoverReport {
        +start: date
        +end: date
        +rows: list~TurnoverRow~
    }

    class TurnoverRow {
        +nomenclature: NomenclatureModel
        +warehouse: WarehouseModel
        +range: RangeModel
        +opening: int | float
        +income: int | float
        +outcome: int | float
        +closing: int | float
    }

    class Prototype~T~
    class StorageManager
    class TransactionModel
    class FilterDto
    class OperationException

    TurnoverRequestDto --> FilterDto : filter
    TurnoverService --> StorageManager : transactions
    TurnoverService ..> TurnoverRequestDto : build
    TurnoverService ..> Prototype : отбор записей журнала
    TurnoverService ..> TurnoverGroupKeyDto : группировка
    TurnoverService ..> TurnoverAccumulatorDto : агрегация
    TurnoverAccumulatorDto ..> TurnoverRow : создаёт
    Prototype ..> TransactionModel
    TurnoverService ..> TurnoverReport : создаёт
    TurnoverReport "1" *-- "*" TurnoverRow : rows
    TurnoverAccumulatorDto ..> OperationException : разные базовые единицы
```


## Логирование, Наблюдатель, сортировка и табличный экспорт

Логирование построено на шаблоне «Наблюдатель». Источники событий (`EntityService`, `StorageManager`,
`SettingsManager` и HTTP-middleware в `Src/main.py`) не зависят от логгера: они формируют `EventDto`
и передают его в `Observer.notify()`. `LoggerManager` наследует `AbstractManager` и `AbstractObserver`,
подписывается на `Observer` в `load()` и сохраняет каждое событие как неизменяемую `LogModel`.

Для выборки логов `LogService` комбинирует `Prototype` для фильтрации и универсальный `Sorter` поверх
`FieldPathReader` для сортировки любых моделей по пути к публичному полю. Табличная выгрузка отделена
от доменных моделей через `TableDto`: `TableReportFactory` создаёт `TxtTableReport`, `CsvTableReport`
или `MarkdownTableReport`, а результат возвращается в `ReportResult`.

```mermaid
classDiagram
    direction TB

    class LogLevel {
        <<enumeration>>
        DEBUG
        INFO
        ERROR
    }

    class LogSubsystem {
        <<enumeration>>
        CRUD
        WAREHOUSE
        WEB
        SETTINGS
    }

    class EventType {
        <<enumeration>>
        ENTITY_CREATED
        ENTITY_UPDATED
        ENTITY_DELETED
        TRANSACTION_ADDED
        WEB_REQUEST
        WEB_ERROR
        SETTINGS_LOADED
        SETTINGS_CHANGED
    }

    class SortOrder {
        <<enumeration>>
        ASC
        DESC
    }

    class TableExportFormat {
        <<enumeration>>
        TXT
        CSV
        MARKDOWN
    }

    class LogModel {
        +period: datetime
        +subsystem: LogSubsystem
        +level: LogLevel
        +message: str
    }

    class EventDto {
        +event_type: EventType
        +subsystem: LogSubsystem
        +level: LogLevel
        +message: str
        +period: datetime
        +payload: object | None
    }

    class AbstractObserver {
        <<abstract>>
        +handle(event)* None
    }

    class Observer {
        -_handlers$: list~AbstractObserver~
        +add(subscriber)$ None
        +delete(subscriber)$ None
        +notify(event)$ None
        +clear()$ None
        +handlers()$ list~AbstractObserver~
    }

    class LoggerManager {
        -_instance$: LoggerManager | None
        -_logs: list~LogModel~
        +logs: list~LogModel~
        +load() None
        +handle(event) None
        +clear() None
        +save(file_name, content) Path
    }

    class SortDto {
        +field_name: str
        +direction: SortOrder
        +from_dict(data)$ Self
    }

    class LogQueryDto {
        +filter: FilterDto
        +sort: SortDto | None
        +from_dict(data)$ Self
    }

    class Sorter {
        -_reader: FieldPathReader
        +sort(items, sort_dto) list~T~
        -_extract_key(item, field_name) _Sortable
    }

    class TableDto {
        +headers: tuple~str~
        +rows: tuple~tuple~str~~
    }

    class AbstractTableReport {
        <<abstract>>
        +is_binary*: bool
        +media_type*: str
        +file_extension*: str
        +build(table)* ReportResult
    }

    class TxtTableReport
    class CsvTableReport
    class MarkdownTableReport

    class TableReportFactory {
        +create(export_format) AbstractTableReport
    }

    class LogService {
        +query(request) list~LogModel~
        +export(export_format, request) ReportResult
    }

    class BaseEntity
    class AbstractManager
    class FieldPathReader
    class Prototype~T~
    class FilterDto
    class ReportResult

    BaseEntity <|-- LogModel
    LogModel --> LogSubsystem : subsystem
    LogModel --> LogLevel : level
    EventDto --> EventType : event_type
    EventDto --> LogSubsystem : subsystem
    EventDto --> LogLevel : level
    Observer o-- AbstractObserver : _handlers
    Observer ..> EventDto
    AbstractManager <|-- LoggerManager
    AbstractObserver <|.. LoggerManager
    LoggerManager o-- LogModel : _logs
    LoggerManager ..> Observer : подписка в load
    SortDto --> SortOrder : direction
    LogQueryDto --> FilterDto : filter
    LogQueryDto --> SortDto : sort
    Sorter *-- FieldPathReader : _reader
    Sorter ..> SortDto
    AbstractTableReport <|-- TxtTableReport
    AbstractTableReport <|-- CsvTableReport
    AbstractTableReport <|-- MarkdownTableReport
    AbstractTableReport ..> TableDto
    AbstractTableReport ..> ReportResult
    TableReportFactory ..> TableExportFormat
    TableReportFactory ..> AbstractTableReport : создаёт
    LogService --> LoggerManager : logs
    LogService --> Sorter
    LogService --> TableReportFactory
    LogService ..> Prototype : фильтрация
    LogService ..> LogQueryDto
    LogService ..> TableDto
```
