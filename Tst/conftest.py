from collections.abc import Iterator

import pytest
from Src.Core.abstract_manager import AbstractManager


def _reset_manager_instances() -> None:
    """Сбрасывает единственные экземпляры у всех подклассов AbstractManager."""
    stack: list[type] = [AbstractManager]
    while stack:
        cls = stack.pop()
        stack.extend(cls.__subclasses__())
        if "_instance" in vars(cls):
            cls._instance = None  # pyright: ignore[reportAttributeAccessIssue, reportPrivateUsage]


@pytest.fixture(autouse=True)
def reset_manager_instances() -> Iterator[None]:
    """Сбрасывает экземпляры менеджеров до и после каждого теста.

    Менеджеры — синглтоны, и без сброса состояние одного теста попадало бы в другой.
    """
    _reset_manager_instances()
    yield
    _reset_manager_instances()
