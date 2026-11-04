import uuid
from typing import ClassVar

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.base_entity import BaseEntity
from Src.Core.common_validator import CommonValidator
from Src.Core.exception import ArgumentsException


class DeserializerFactory:
    """Фабрика десериализаторов: по целевому типу выбирает десериализатор и рекурсивно собирает модель.

    Клиент вызывает только ``deserialize(target_type, data)``. Это обратная сторона ``ConverterFactory``.

    Проектные решения:

    - Десериализатор выбирается по **целевому типу** (что ждёт конструктор), а не по типу значения, как у
      конвертеров: у значения из JSON своего типа нет. Выбор по точному типу, без обхода MRO: нужна именно та
      модель, которую запросили.
    - Сопоставление «тип модели — класс десериализатора» лежит в ``_deserializers``, как в ``ReportFactory``.
      Новая модель подключается строкой в нём.
    - Рекурсия идёт через функцию: фабрика передаёт десериализаторам ``_resolve``, а они вызывают её
      для вложенных моделей. Десериализаторы не зависят от класса фабрики, цикла импортов нет.
    - Все десериализаторы одной загрузки делят один кэш собранных моделей по идентификатору. Поэтому единица
      измерения, вложенная полным словарём в каждую номенклатуру, собирается один раз, а не копируется.
    - Кэш живёт только на время ``deserialize``: следующая загрузка начинается с чистого. Из-за кэша фабрика
      хранит состояние и не годится для параллельных вызовов.
    """

    # Сопоставление типа модели и класса её десериализатора
    _deserializers: ClassVar[dict[type, type[AbstractDeserializer]]] = {}

    # Собранные модели по идентификатору, общий для всех десериализаторов одной загрузки
    _cache: dict[uuid.UUID, BaseEntity]

    def __init__(self) -> None:
        """Инициализирует фабрику с пустым кэшем."""
        self._cache = {}

    def create(self, target_type: type) -> AbstractDeserializer:
        """Создаёт десериализатор для указанного типа модели.

        Десериализатор получает функцию рекурсии и общий кэш фабрики.

        :param target_type: Тип модели, которую нужно собрать.
        :return: Новый десериализатор этой модели.
        :raises ArgumentsException: Если значение не тип или для типа нет десериализатора.
        """
        target_type = CommonValidator.validate_instance(target_type, type, "target_type", "Ожидается тип модели")
        deserializer = self._deserializers.get(target_type)
        if deserializer is None:
            raise ArgumentsException("target_type", f"Нет десериализатора для {target_type.__name__}")

        return deserializer(self._resolve, self._cache)

    def deserialize[T](self, target_type: type[T], data: object) -> T:
        """Превращает данные из JSON в модель заданного типа, вложенные модели собирает рекурсивно.

        Это точка входа для клиента. Десериализаторы её не вызывают, для вложенных моделей у них
        есть ``_resolve``: иначе кэш сбросился бы посреди загрузки.

        :param target_type: Тип модели, которую нужно собрать.
        :param data: Словарь полей модели, как его записал ``ConverterFactory``.
        :return: Собранная модель.
        :raises ArgumentsException: Если нет десериализатора для типа, данные некорректны
            или десериализатор вернул модель другого типа.
        :raises OperationException: Если в данных есть ссылка на модель, которой нет в данных.
        """
        try:
            model = self._resolve(target_type, data)
            return CommonValidator.validate_instance(
                model, target_type, "target_type", f"Десериализатор вернул не {target_type.__name__}"
            )
        finally:
            self._cache.clear()

    def _resolve(self, target_type: type, data: object) -> object:
        """Собирает модель заданного типа, кэш не сбрасывает: вызывается рекурсивно из десериализаторов.

        :param target_type: Тип модели, которую нужно собрать.
        :param data: Данные модели.
        :return: Собранная модель.
        :raises ArgumentsException: Если нет десериализатора для типа или данные некорректны.
        :raises OperationException: Если в данных есть ссылка на неизвестную модель.
        """
        # Рекурсия: десериализатор в _build снова вызовет эту функцию для вложенных моделей
        return self.create(target_type).deserialize(data)
