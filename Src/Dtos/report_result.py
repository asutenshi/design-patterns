from typing import override

from fastapi import Response
from Src.Core.common_validator import CommonValidator


class ReportResult:
    """Результат формирования отчёта: содержимое и способ его выдачи.

    Один класс на все форматы: отчёты различаются только содержимым и тремя признаками
    выдачи (файл или текст, MIME-тип, расширение), которые задаёт сам отчёт при создании результата.
    Результат — объект-значение: у него нет идентификатора, он неизменяем, а равенство определяется
    содержимым и способом выдачи. Поэтому два отчёта по одним и тем же данным равны. Если отчёты
    понадобится хранить, хранимой сущностью станет отдельная запись (дата, параметры, ответственный),
    а результат войдёт в неё полем.

    Содержимое доступно и текстом, и байтами. ``is_binary`` подсказывает, как его отдавать:
    файлом на скачивание или текстом; имя файла дополняется расширением ``file_extension``.
    """

    # Содержимое отчёта
    _text: str
    # Кодировка, в которой текст отдаётся байтами
    _encoding: str
    # Отдаётся ли результат файлом на скачивание
    _is_binary: bool
    # MIME-тип содержимого
    _media_type: str
    # Расширение файла без точки
    _file_extension: str

    def __init__(
        self, text: str, media_type: str, file_extension: str, *, is_binary: bool, encoding: str = "utf-8"
    ) -> None:
        """Инициализирует результат.

        :param text: Содержимое отчёта. Пустая строка допустима: отчёт без данных.
        :param media_type: MIME-тип содержимого, например ``text/plain; charset=utf-8``.
        :param file_extension: Расширение файла с содержимым без точки, например ``txt``.
        :param is_binary: True, если результат отдаётся файлом на скачивание, а не текстом.
        :param encoding: Кодировка, в которой текст отдаётся байтами.
        :raises ArgumentsException: Если text не строка, признак выдачи неверного типа,
            а MIME-тип, расширение или кодировка пусты.
        """
        self._text = CommonValidator.validate_instance(text, str, "text", "Ожидается строка")
        self._media_type = CommonValidator.validate_string(media_type, "media_type")
        self._file_extension = CommonValidator.validate_string(file_extension, "file_extension")
        self._is_binary = CommonValidator.validate_instance(is_binary, bool, "is_binary", "Ожидается логическое значение")
        self._encoding = CommonValidator.validate_string(encoding, "encoding")

    @property
    def text(self) -> str:
        """Возвращает содержимое отчёта текстом."""
        return self._text

    @property
    def binary(self) -> bytes:
        """Возвращает содержимое отчёта в кодировке результата."""
        return self._text.encode(self._encoding)

    @property
    def is_binary(self) -> bool:
        """Возвращает True, если результат отдаётся файлом на скачивание, а не текстом."""
        return self._is_binary

    @property
    def media_type(self) -> str:
        """Возвращает MIME-тип содержимого."""
        return self._media_type

    @property
    def file_extension(self) -> str:
        """Возвращает расширение файла с содержимым без точки."""
        return self._file_extension

    def to_response(self, file_stem: str) -> Response:
        """Превращает результат в HTTP-ответ.

        Результат с ``is_binary`` отдаётся файлом на скачивание: байты и заголовок
        ``Content-Disposition: attachment``. Остальные — текстом с MIME-типом формата.

        :param file_stem: Имя файла без расширения, только ASCII: так его не нужно кодировать в заголовке.
        :return: Ответ с содержимым отчёта.
        """
        if not self._is_binary:
            return Response(content=self._text, media_type=self._media_type)

        file_name = f"{file_stem}.{self._file_extension}"
        return Response(
            content=self.binary,
            media_type=self._media_type,
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )

    @override
    def __eq__(self, value: object, /) -> bool:
        """Сравнивает результаты по содержимому и способу выдачи."""
        if not isinstance(value, ReportResult):
            return NotImplemented
        return self._key() == value._key()  # pyright: ignore[reportPrivateUsage]

    @override
    def __hash__(self) -> int:
        """Возвращает хэш результата на основе содержимого и способа выдачи."""
        return hash(self._key())

    def _key(self) -> tuple[bytes, str, str, bool]:
        """Возвращает значения, по которым сравниваются результаты."""
        return (self.binary, self._media_type, self._file_extension, self._is_binary)
