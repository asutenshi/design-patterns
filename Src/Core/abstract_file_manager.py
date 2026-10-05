from abc import ABC, abstractmethod
from typing import Any, override

from Src.Core.abstract_manager import AbstractManager


class AbstractFileManager(AbstractManager, ABC):
    """Базовый класс менеджеров, читающих данные из файла.

    Порядок работы задаёт load(): чтение сырых данных, затем convert().
    Наследники реализуют _read() и convert(), но не переопределяют load().
    """

    # Загруженные сырые данные
    _data: dict[str, Any]

    @override
    def _initialize(self) -> None:
        """Готовит флаг загрузки и пустые сырые данные."""
        super()._initialize()
        self._data = {}

    @override
    def load(self, file_name: str = "") -> None:
        """Читает сырые данные из файла и преобразует их в модели.

        Флаг is_loaded выставляется только после успешного convert(). При ошибке
        он остаётся False, а сырые данные сбрасываются.

        :param file_name: Путь к файлу, пустая строка — файл по умолчанию.
        :raises OperationException: Если данные не удалось прочитать или преобразовать.
        """
        self._is_loaded = False
        self._data = {}
        self._data = self._read(file_name)
        self.convert()
        self._is_loaded = True

    @abstractmethod
    def _read(self, file_name: str) -> dict[str, Any]:
        """Читает сырые данные из файла.

        :param file_name: Путь к файлу, пустая строка — файл по умолчанию.
        :return: Сырые данные.
        :raises OperationException: Если файл недоступен или данные повреждены.
        """

    @abstractmethod
    def convert(self) -> None:
        """Преобразует сырые данные из _data в доменные модели.

        :raises OperationException: Если данных не хватает или они некорректны.
        """
