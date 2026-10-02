from collections.abc import Iterator

import pytest
from Src.Core.abstract_manager import AbstractManager


@pytest.fixture(autouse=True)
def reset_manager_instances() -> Iterator[None]:
    """Очищает реестр менеджеров до и после каждого теста.

    Менеджеры — синглтоны, и без очистки состояние одного теста попадало бы в другой.
    """
    AbstractManager._instances.clear()  # pyright: ignore[reportPrivateUsage]
    yield
    AbstractManager._instances.clear()  # pyright: ignore[reportPrivateUsage]