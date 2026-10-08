# Диаграммы классов

Диаграммы описывают реализованный код в `Src/`, а не планы из `Docs/DomainEntities.md`.
При добавлении, переименовании или удалении класса обновляйте соответствующую диаграмму.
Mermaid отображается в GitHub и в IDE с поддержкой Markdown.

## Модели

Все модели лежат в `Src/Models/`, базовые классы — в `Src/Core/`.
Стрелка с пустым треугольником — наследование, обычная стрелка — хранимая ссылка на другую модель.

```mermaid
classDiagram
    direction TB

    class BaseEntity {
        <<abstract>>
        +id: UUID
    }

    note for BaseEntity "Равенство и хэш определяются по id и типу"

    class NamedEntity {
        <<abstract>>
        +name: str
    }

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
        +gross_weight: float
        +net_weight: float
    }

    note for IngredientModel "Строка состава технологической карты: часть карты, без id. nomenclature только для чтения. Количество в базовой единице номенклатуры, веса вычисляются"

    class RecipeModel {
        +RESULT_TYPES: frozenset~NomenclatureType~
        +result: NomenclatureModel
        +output_quantity: int | float
        +cooking_time_minutes: int | float
        +steps: list~str~
        +ingredients: list~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +add_ingredient(ingredient) None
        +remove_ingredient(nomenclature) None
        +create_beef_bouillon(nomenclatures)$ RecipeModel
        +create_boiled_beef(nomenclatures)$ RecipeModel
        +create_beet_fry(nomenclatures)$ RecipeModel
        +create_borscht(nomenclatures)$ RecipeModel
    }

    note for RecipeModel "Результат (полуфабрикат или блюдо) только для чтения. Ингредиенты уникальны по номенклатуре. Веса брутто и нетто вычисляются как суммы по ингредиентам. Карту полуфабриката находят по result. Фабрики карт принимают словарь «наименование → номенклатура» и бросают ArgumentsException, если нужной позиции в нём нет"

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
    }

    class OrganizationModel {
        +BIC_LENGTH = 9
        +ACCOUNT_LENGTH = 20
        +inn: str
        +bic: str
        +account: str
        +ownership_form: OwnershipForm
    }

    class OwnershipForm {
        <<enumeration>>
        LLC
        JSC
        PJSC
        SOLE_PROPRIETOR
    }

    BaseEntity <|-- NamedEntity
    BaseEntity <|-- SettingsModel
    NamedEntity <|-- RangeModel
    NamedEntity <|-- NomenclatureModel
    NamedEntity <|-- NomenclatureGroupModel
    NamedEntity <|-- WarehouseModel
    NamedEntity <|-- OrganizationModel
    NamedEntity <|-- RecipeModel

    NomenclatureModel --> NomenclatureGroupModel : group
    NomenclatureModel --> RangeModel : range
    NomenclatureModel --> NomenclatureType : type
    IngredientModel --> NomenclatureModel : nomenclature
    RecipeModel --> NomenclatureModel : result
    RecipeModel "1" *-- "*" IngredientModel : ingredients
    RangeModel --> RangeModel : base
    OrganizationModel --> OwnershipForm : ownership_form
    SettingsModel --> OrganizationModel : organization
```

## Рецепты

Модели технологических карт (п. 2.1 и 2.5 ТЗ) и то, как они связаны с номенклатурой и хранилищем.
Те же классы показаны на общей диаграмме выше, здесь оставлено только относящееся к рецептам.

- Карта (`RecipeModel`) получает одну номенклатуру-результат: полуфабрикат или блюдо.
- Состав — строки `IngredientModel` без собственного `id`: внутри карты строку определяет номенклатура.
  Ингредиент хранит количество в базовой единице номенклатуры и долю потерь.
- Вес ингредиента: брутто = `quantity * grams_per_base_unit`, нетто = брутто * (1 − `loss_ratio`).
  Вес карты — сумма по ингредиентам, вычисляется при каждом обращении.
- Полуфабрикат входит в состав как обычная номенклатура, его карту находит `StorageManager.find_recipe()`
  по результату. Упаковка — обычный ингредиент.
- Фабрики `create_*` собирают карты из `Recipes.md` по словарю «наименование → номенклатура».

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
        +gross_weight: float
        +net_weight: float
    }

    note for IngredientModel "Строка состава карты, без id. loss_ratio от 0 включительно до 1 не включая. Упаковка — обычный ингредиент без потерь"

    class RecipeModel {
        +RESULT_TYPES: frozenset~NomenclatureType~
        +result: NomenclatureModel
        +output_quantity: int | float
        +cooking_time_minutes: int | float
        +steps: list~str~
        +ingredients: list~IngredientModel~
        +gross_weight: float
        +net_weight: float
        +add_ingredient(ingredient) None
        +remove_ingredient(nomenclature) None
        +create_beef_bouillon(nomenclatures)$ RecipeModel
        +create_boiled_beef(nomenclatures)$ RecipeModel
        +create_beet_fry(nomenclatures)$ RecipeModel
        +create_borscht(nomenclatures)$ RecipeModel
    }

    note for RecipeModel "Результат — только SEMI_FINISHED или DISH, задаётся в конструкторе. Брутто, нетто и выход (output_quantity * grams_per_base_unit результата) не сверяются друг с другом. Результат не может быть ингредиентом своей карты"

    class UniqueCollection~T~ {
        +add(item) None
        +remove(key) None
    }

    note for UniqueCollection "В RecipeModel ключ — id номенклатуры ингредиента, в StorageManager — id результата карты"

    class StorageManager {
        +recipes: list~RecipeModel~
        +find_recipe(nomenclature) RecipeModel | None
        -_add_recipe(recipe) None
        -_creates_cycle(recipe) bool
    }

    note for StorageManager "Одна карта на номенклатуру-результат. При регистрации обходит карты вложенных полуфабрикатов и отвергает цикл (A включает B, B включает A)"

    class ArgumentsException

    NomenclatureModel --> NomenclatureType : type
    IngredientModel --> NomenclatureModel : nomenclature
    RecipeModel --> NomenclatureModel : result
    RecipeModel "1" *-- "*" IngredientModel : ingredients
    RecipeModel *-- UniqueCollection : ingredients
    StorageManager *-- UniqueCollection : recipes
    StorageManager --> RecipeModel : recipes
    RecipeModel ..> ArgumentsException : нет номенклатуры в словаре, дубликат, результат в составе
    StorageManager ..> ArgumentsException : цикл включений, вторая карта на результат
```

Пример составной карты: «Борщ с говядиной» (блюдо) включает полуфабрикаты «Бульон костный говяжий»,
«Говядина отварная», «Зажарка свекольная» и упаковку «Контейнер для супа 500 мл». Каждый полуфабрикат
собирается по своей карте только из сырья, поэтому циклов в начальных данных нет.

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
        +validate_fraction(value, field)$ int | float
        +validate_digits(value, field, lengths)$ str
        +validate_instance(value, expected_type, field, message)$ T
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
    class RecipeModel
    class OrganizationModel
    class SettingsModel

    Exception <|-- ProjectException
    ProjectException <|-- ArgumentsException
    ProjectException <|-- OperationException
    InnValidator ..> CommonValidator : формат и цифры
    CommonValidator ..> ArgumentsException : бросает
    InnValidator ..> ArgumentsException : бросает
    BaseEntity ..> ArgumentsException : id
    NamedEntity ..> CommonValidator : name
    RangeModel ..> CommonValidator : factor, base
    NomenclatureModel ..> CommonValidator : name, full_name, group, range, type, grams_per_base_unit
    IngredientModel ..> CommonValidator : nomenclature, quantity, loss_ratio
    RecipeModel ..> CommonValidator : result, output_quantity, cooking_time_minutes, steps, ingredient, nomenclature
    RecipeModel ..> ArgumentsException : тип результата, шаги, результат как ингредиент
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

Читает `settings.json` и собирает из него `SettingsModel`. Ошибки модели (`ArgumentsException`) превращает
в `OperationException`, чтобы вызывающий код ловил одно исключение.

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
        -_values(model, data, optional)$ dict
        +convert() None
    }

    note for SettingsManager "Singleton: __new__ создаёт экземпляр один раз и вызывает _initialize(). Файл по умолчанию settings.json в корне проекта. Если файл не читается, берутся настройки по умолчанию, отсутствующий файл создаётся. Модель присваивается только целиком, при ошибке прежние настройки не затираются"

    class SettingsModel {
        +organization: OrganizationModel
        +boss_name: str
        +account_name: str
        +is_first_start: bool
    }

    class OrganizationModel
    class OwnershipForm {
        <<enumeration>>
    }
    class ArgumentsException
    class OperationException

    AbstractManager <|-- AbstractFileManager
    AbstractFileManager <|-- SettingsManager
    SettingsManager --> SettingsModel : settings
    SettingsModel --> OrganizationModel : organization
    OrganizationModel --> OwnershipForm : ownership_form
    SettingsManager ..> Common : путь к файлу, поля моделей
    Common ..> OperationException : бросает
    SettingsManager ..> OrganizationModel : создаёт в convert()
    SettingsManager ..> OwnershipForm : значение из файла
    SettingsManager ..> ArgumentsException : перехватывает
    SettingsManager ..> OperationException : бросает
```

### StorageManager

Хранит доменные модели в пяти коллекциях без дубликатов. При первом запуске (`is_first_start` в настройках)
`load()` наполняет их начальными данными через фабричные методы моделей: 5 единиц измерения, 7 групп,
24 номенклатуры, 2 склада и 4 технологические карты из `Recipes.md`.
Номенклатура ссылается на те же объекты единиц и групп, что лежат в коллекциях, а карты — на те же объекты номенклатуры, а не на копии.
Карта регистрируется с проверкой циклов: обходятся карты вложенных полуфабрикатов (глубокая защита, локальную делает `RecipeModel`).
Карту полуфабриката находит `find_recipe()` по номенклатуре-результату, на одну позицию допускается одна карта.
Хранилище зависит от менеджера настроек: `load(settings_manager)` принимает его параметром, по умолчанию берёт
единственный `SettingsManager`. Настройки должны быть загружены до `StorageManager.load()`, сам `load()` их не загружает.
С файлами `StorageManager` не работает, поэтому наследует `AbstractManager`, а не `AbstractFileManager`.

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
        -_ranges: UniqueCollection~RangeModel~
        -_nomenclature_groups: UniqueCollection~NomenclatureGroupModel~
        -_nomenclatures: UniqueCollection~NomenclatureModel~
        -_warehouses: UniqueCollection~WarehouseModel~
        -_recipes: UniqueCollection~RecipeModel~
        +ranges: list~RangeModel~
        +nomenclature_groups: list~NomenclatureGroupModel~
        +nomenclatures: list~NomenclatureModel~
        +warehouses: list~WarehouseModel~
        +recipes: list~RecipeModel~
        +__new__() Self
        +load(settings_manager) None
        +find_recipe(nomenclature) RecipeModel | None
        #_initialize() None
        -_reset_collections() None
        -_fill_first_start_data() None
        -_create_nomenclatures() list~NomenclatureModel~
        -_add_recipe(recipe) None
        -_creates_cycle(recipe) bool
    }

    note for StorageManager "Singleton: __new__ создаёт экземпляр один раз и вызывает _initialize(). Свойства возвращают копии списков. load() каждый раз пересоздаёт коллекции. Ключ коллекции карт — id результата"

    class UniqueCollection~T~ {
        -_key: Callable~T, Hashable~
        -_items: dict~Hashable, T~
        +add(item) None
        +remove(key) None
    }

    note for UniqueCollection "Ключ уникальности задаёт функция: в StorageManager это name.casefold() (регистр не учитывается), в RecipeModel — id номенклатуры. add принимает элемент, remove — ключ. Поддерживает итерацию и len()"

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
    class ArgumentsException
    class OperationException

    AbstractManager <|-- StorageManager
    StorageManager "1" *-- "5" UniqueCollection : коллекции
    StorageManager ..> SettingsManager : зависимость, параметр load(), читает is_first_start
    StorageManager --> RangeModel : ranges
    StorageManager --> NomenclatureGroupModel : nomenclature_groups
    StorageManager --> NomenclatureModel : nomenclatures
    StorageManager --> WarehouseModel : warehouses
    StorageManager --> RecipeModel : recipes
    NomenclatureModel --> NomenclatureGroupModel : group
    NomenclatureModel --> RangeModel : range
    RangeModel --> RangeModel : base
    UniqueCollection ..> ArgumentsException : бросает при дубликате и удалении отсутствующего ключа
    StorageManager ..> OperationException : бросает
```
