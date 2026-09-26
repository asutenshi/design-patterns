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
    }

    class NomenclatureModel {
        +NAME_MAX_LENGTH = 50
        +FULL_NAME_MAX_LENGTH = 255
        +full_name: str
        +group: NomenclatureGroupModel
        +range: RangeModel
    }

    class NomenclatureGroupModel

    class WarehouseModel

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
    NamedEntity <|-- RangeModel
    NamedEntity <|-- NomenclatureModel
    NamedEntity <|-- NomenclatureGroupModel
    NamedEntity <|-- WarehouseModel
    NamedEntity <|-- OrganizationModel

    NomenclatureModel --> NomenclatureGroupModel : group
    NomenclatureModel --> RangeModel : range
    RangeModel --> RangeModel : base
    OrganizationModel --> OwnershipForm : ownership_form
```

## Проверки и ошибки

Все проверки бросают `ArgumentsException`. Модели вызывают валидаторы из сеттеров.

```mermaid
classDiagram
    direction LR

    class CommonValidator {
        +validate_string(value, field, max_length)$ str
        +validate_positive_number(value, field)$ int | float
        +validate_digits(value, field, lengths)$ str
        +validate_instance(value, expected_type, field, message)$ T
    }

    class InnValidator {
        +LENGTHS: tuple~int~
        +validate(value, field)$ str
    }

    class ArgumentsException {
        -_field: str
        -_message: str
        -_stack_trace: str
    }

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
    class OrganizationModel

    Exception <|-- ArgumentsException
    InnValidator ..> CommonValidator : формат и цифры
    CommonValidator ..> ArgumentsException : бросает
    InnValidator ..> ArgumentsException : бросает
    BaseEntity ..> ArgumentsException : id
    NamedEntity ..> CommonValidator : name
    RangeModel ..> CommonValidator : factor, base
    NomenclatureModel ..> CommonValidator : name, full_name, group, range
    OrganizationModel ..> CommonValidator : bic, account, ownership_form
    OrganizationModel ..> InnValidator : inn
```
