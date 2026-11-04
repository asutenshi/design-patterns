from typing import cast, override

from Src.Core.abstract_deserializer import AbstractDeserializer
from Src.Core.common_validator import CommonValidator
from Src.Models.range_model import RangeModel


class RangeDeserializer(AbstractDeserializer):
    """Десериализатор единицы измерения.

    Базовая единица ссылается сама на себя, и сериализатор записывает это ссылкой ``{"id": <собственный id>}``.
    Конструктор ждёт для базовой единицы ``base=None``, поэтому такая ссылка здесь не разворачивается
    рекурсивно (иначе рекурсия не закончилась бы), а превращается в ``None``. Производная единица хранит базовую
    полным словарём, её десериализатор вызывается рекурсивно, и базовая единица попадает в кэш.
    Вычисляемое поле ``is_base`` игнорируется.
    """

    @override
    def _build(self, data: dict[str, object]) -> object:
        """Создаёт единицу измерения по полям ``name``, ``factor`` и ``base``.

        :param data: Словарь полей единицы измерения.
        :return: Новая единица измерения.
        :raises ArgumentsException: Если поля отсутствуют или некорректны.
        :raises OperationException: Если базовая единица — ссылка на модель, которой нет в данных.
        """
        name = cast(str, CommonValidator.validate_field(data, "name"))
        factor = cast(float, CommonValidator.validate_field(data, "factor"))
        base_data = CommonValidator.validate_dict(CommonValidator.validate_field(data, "base"), "base")

        # Базовая единица ссылается сама на себя: в данных только её собственный id
        own_id = self._read_id(data)
        is_self_reference = own_id is not None and len(base_data) == 1 and self._read_id(base_data) == own_id
        base = None if is_self_reference else self._nested(RangeModel, base_data)
        return RangeModel(name, factor, base)
