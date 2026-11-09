import inspect
from abc import ABC, abstractmethod
from typing import ClassVar, Self

from Src.Core.exception import ArgumentsException


class AbstractModel(ABC):
    """Корень всех доменных моделей: знает свой тип и умеет создаваться из словаря.

    Обе возможности нужны для загрузки из JSON без знания о конкретных моделях снаружи:

    - ``model_type`` — полное имя класса (``Src.Models.range_model.RangeModel``). Это публичное свойство,
      поэтому ``ConverterFactory`` записывает его в JSON сам, наравне с другими полями. По нему десериализатор
      понимает, какую модель собирать;
    - ``from_dict`` — фабричный метод модели: конструктор вызывает только сама модель, и при его изменении
      правится одно место. Вложенные модели в словаре уже собраны, модель лишь раскладывает значения
      по аргументам конструктора.

    Класс по ``model_type`` ищется в реестре наследников, а не импортом модуля по строке из файла:
    так из файла нельзя заставить выполнить произвольный модуль. Наследник попадает в реестр,
    когда его модуль импортирован. Модели, которые хранит хранилище, импортирует ``StorageManager``.

    Идентификатор сюда не входит: он есть только у сущностей (``BaseEntity``), а у строки состава карты
    (``IngredientModel``) его нет.
    """

    # Имя поля, под которым тип модели записывается в JSON: совпадает с именем свойства model_type
    TYPE_FIELD: ClassVar[str] = "model_type"

    # Наследники по полному имени класса
    _registry: ClassVar[dict[str, type["AbstractModel"]]] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Регистрирует наследника по полному имени класса.

        Абстрактные классы тоже попадают в реестр: на этом этапе Python ещё не знает, абстрактен ли класс.
        Их отсекает ``resolve_type``.

        :param kwargs: Параметры класса, передаются дальше по цепочке.
        """
        super().__init_subclass__(**kwargs)
        AbstractModel._registry[AbstractModel._type_name(cls)] = cls

    @property
    def model_type(self) -> str:
        """Возвращает тип модели: полное имя её класса (модуль и имя класса)."""
        return AbstractModel._type_name(type(self))

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Фабричный метод: создаёт модель из словаря её полей.

        Вложенные модели в словаре уже собраны. Вычисляемые и служебные поля (``id``, ``model_type``,
        веса) модель игнорирует: идентификатор выставит тот, кто загружает.

        :param data: Поля модели по именам, как их записал ``ConverterFactory``.
        :return: Новая модель.
        :raises ArgumentsException: Если обязательного поля нет или значение не проходит проверку модели.
        """

    @staticmethod
    def resolve_type(model_type: object) -> type["AbstractModel"]:
        """Возвращает класс модели по её типу.

        :param model_type: Тип модели, как его возвращает ``model_type``.
        :return: Класс модели.
        :raises ArgumentsException: Если значение не строка, такой модели нет в реестре или она абстрактная.
        """
        if not isinstance(model_type, str):
            raise ArgumentsException(AbstractModel.TYPE_FIELD, "Тип модели должен быть строкой")

        cls = AbstractModel._registry.get(model_type)
        if cls is None or inspect.isabstract(cls):
            raise ArgumentsException(AbstractModel.TYPE_FIELD, f"Неизвестный тип модели: {model_type}")
        return cls

    @staticmethod
    def _type_name(model_class: type) -> str:
        """Возвращает полное имя класса: модуль и имя класса.

        :param model_class: Класс модели.
        :return: Строка вида ``Src.Models.range_model.RangeModel``.
        """
        return f"{model_class.__module__}.{model_class.__qualname__}"
