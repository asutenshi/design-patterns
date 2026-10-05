import json
from typing import Any, ClassVar, Self, cast, override

from Src.Core.abstract_file_manager import AbstractFileManager
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.ownership_form import OwnershipForm
from Src.Models.organization_model import OrganizationModel
from Src.Models.settings_model import SettingsModel


class SettingsManager(AbstractFileManager):
    """Менеджер настроек (Singleton): читает settings.json и собирает SettingsModel."""

    # Единственный экземпляр этого класса
    _instance: ClassVar["SettingsManager | None"] = None

    # Файл настроек по умолчанию, путь относительно текущего каталога
    _default_file_name: str = "settings.json"

    # Загруженные настройки, None до первой успешной загрузки
    _settings: SettingsModel | None

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса, при первом обращении создаёт его.

        Состояние готовится здесь, а не в __init__: Python вызывает __init__
        при каждом обращении к классу. Экземпляр ищется в cls.__dict__, а не через
        getattr, чтобы наследник не получил экземпляр родителя.
        """
        instance = cast(Self | None, cls.__dict__.get("_instance"))
        if instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            # Сохранение после хука: если он упадёт, полусозданного экземпляра не останется
            cls._instance = instance
        return instance

    @override
    def _initialize(self) -> None:
        """Создаёт пустое хранилище настроек."""
        super()._initialize()
        self._settings = None

    @override
    def _read(self, file_name: str) -> dict[str, Any]:
        """Читает JSON-файл настроек.

        :param file_name: Путь к файлу, пустая строка — файл по умолчанию.
        :return: Содержимое файла.
        :raises OperationException: Если файл недоступен, не является JSON-объектом
            или не читается как UTF-8.
        """
        path = file_name.strip() or self._default_file_name
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError) as ex:
            raise OperationException(f"Не удалось прочитать файл настроек {path}: {ex}") from ex

        if not isinstance(data, dict):
            raise OperationException(f"Файл настроек {path} должен содержать JSON-объект")
        return data

    @override
    def convert(self) -> None:
        """Собирает SettingsModel из прочитанных данных.

        Модель присваивается только целиком: при ошибке прежние настройки не затираются
        наполовину собранными.

        :raises OperationException: Если нет обязательного ключа, значение имеет
            неверный тип или не проходит проверку модели.
        """
        try:
            org = self._data["organization"]
            organization = OrganizationModel(
                name=org["name"],
                inn=org["inn"],
                bic=org["bic"],
                account=org["account"],
                ownership_form=OwnershipForm(org["ownership_form"]),
            )
            self._settings = SettingsModel(
                organization=organization,
                boss_name=self._data["boss_name"],
                account_name=self._data["account_name"],
                is_first_start=self._data.get("is_first_start", True),
            )
        except KeyError as ex:
            raise OperationException(f"В настройках нет обязательного поля {ex}") from ex
        except (TypeError, ValueError, ArgumentsException) as ex:
            raise OperationException(f"Некорректные настройки: {ex}") from ex

    @property
    def settings(self) -> SettingsModel:
        """Возвращает загруженные настройки.

        :raises OperationException: Если настройки ещё не загружены или последняя загрузка не удалась.
        """
        if not self.is_loaded or self._settings is None:
            raise OperationException("Настройки не загружены, вызовите load()")
        return self._settings
