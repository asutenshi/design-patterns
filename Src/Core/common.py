from pathlib import Path
from typing import ClassVar

from Src.Core.exception import OperationException


class Common:
    """Набор общих вспомогательных функций, не привязанных к конкретной сущности."""

    # Файл, по которому определяется корень проекта
    _ROOT_MARKER: ClassVar[str] = "pyproject.toml"

    @staticmethod
    def find_project_root(start: Path | None = None) -> Path:
        """Находит корень проекта: ближайший каталог вверх по дереву с pyproject.toml.

        По умолчанию поиск идёт от расположения этого файла, а не от текущего каталога,
        поэтому результат не зависит от того, откуда запущено приложение.

        :param start: Файл или каталог, с которого начинается поиск, None — этот файл.
        :return: Абсолютный путь к корню проекта.
        :raises OperationException: Если ни в одном из родительских каталогов нет pyproject.toml.
        """
        origin = (start or Path(__file__)).resolve()
        for directory in (origin, *origin.parents):
            if (directory / Common._ROOT_MARKER).is_file():
                return directory
        raise OperationException(f"Не найден корень проекта: нет {Common._ROOT_MARKER} выше {origin}")

    @staticmethod
    def resolve_path(file_name: str, default_name: str) -> Path:
        """Возвращает полный путь к файлу.

        Пустая строка — файл default_name в корне проекта. Переданный путь берётся
        как есть, относительный отсчитывается от текущего каталога.

        :param file_name: Путь к файлу, пустая строка — файл по умолчанию.
        :param default_name: Имя файла по умолчанию, ищется в корне проекта.
        :return: Абсолютный путь.
        :raises OperationException: Если нужен файл по умолчанию, но корень проекта не найден.
        """
        name = file_name.strip()
        if not name:
            return Common.find_project_root() / default_name
        return Path(name).expanduser().resolve()
