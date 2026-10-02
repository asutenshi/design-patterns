from abc import ABC, abstractmethod
from typing import Any, ClassVar, Self, cast


class AbstractManager(ABC):
    """Базовый класс менеджеров: загрузка данных и преобразование их в модели.

    Менеджер — Singleton: на каждый конкретный класс создаётся один экземпляр.
    Порядок работы задаёт load(): чтение сырых данных, затем convert().
    Наследники реализуют _read() и convert(), но не переопределяют load().
    Собственное состояние наследника готовится в хуке _initialize().
    """

    # Единственные экземпляры менеджеров по конкретным классам
    _instances: ClassVar[dict[type, "AbstractManager"]] = {}

    # Флаг. Загрузка и обработка завершена успешно
    _is_loaded: bool
    # Загруженные сырые данные
    _data: dict[str, Any]

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса, при первом обращении создаёт его.

        Состояние готовится здесь, а не в __init__: Python вызывает __init__
        при каждом обращении к классу, а состояние нужно создать ровно один раз.
        """
        instance = cls._instances.get(cls)
        if instance is None:
            instance = super().__new__(cls)
            instance._is_loaded = False
            instance._data = {}
            instance._initialize()
            # Регистрация после хука: если он упадёт, в реестре не останется полусозданный экземпляр
            cls._instances[cls] = instance
        return cast(Self, instance)

    def _initialize(self) -> None:
        """Хук: готовит собственное состояние наследника при первом создании экземпляра.

        Вызывается один раз, до регистрации экземпляра в реестре. Базовая реализация
        пустая: переопределять её и вызывать super() не обязательно. Обращаться
        к другим менеджерам из хука нельзя, такие зависимости разрешаются в convert().
        """

    def load(self, file_name: str = "") -> None:
        """Читает сырые данные и преобразует их в модели.

        Флаг is_loaded выставляется только после успешного convert(). При ошибке
        он остаётся False, а сырые данные сбрасываются.

        :param file_name: Источник данных, пустая строка — источник по умолчанию.
        :raises OperationException: Если данные не удалось прочитать или преобразовать.
        """
        self._is_loaded = False
        self._data = {}
        self._data = self._read(file_name)
        self.convert()
        self._is_loaded = True

    @abstractmethod
    def _read(self, file_name: str) -> dict[str, Any]:
        """Читает сырые данные из источника.

        :param file_name: Источник данных, пустая строка — источник по умолчанию.
        :return: Сырые данные.
        :raises OperationException: Если источник недоступен или данные повреждены.
        """

    @abstractmethod
    def convert(self) -> None:
        """Преобразует сырые данные из _data в доменные модели.

        :raises OperationException: Если данных не хватает или они некорректны.
        """

    @property
    def is_loaded(self) -> bool:
        """Возвращает True, если загрузка и преобразование завершены успешно."""
        return self._is_loaded
