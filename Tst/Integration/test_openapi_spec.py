import os
from pathlib import Path
from typing import cast

import pytest
import yaml
from Src.main import app

# Описание API в репозитории: его видно без запуска приложения, а тест следит, чтобы оно не устарело
_SPEC_PATH = Path(__file__).resolve().parents[2] / "Docs" / "openapi.yaml"
# Переменная окружения, с которой тест перезаписывает описание свежим из приложения
_UPDATE_EXAMPLE_ENV = "UPDATE_EXAMPLES"


class _SpecDumper(yaml.SafeDumper):
    """Записывает многострочные строки (описания из docstring) блоком ``|``, чтобы их было удобно читать."""


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    """Выбирает стиль строки: блок для многострочной, обычный для остальных."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|" if "\n" in value else None)


_SpecDumper.add_representer(str, _represent_str)


def _read_spec() -> dict[str, object]:
    """Читает openapi.yaml из репозитория."""
    return cast(dict[str, object], yaml.safe_load(_SPEC_PATH.read_text(encoding="utf-8")))


def test_openapi_yaml_matches_application_spec():
    """Docs/openapi.yaml совпадает с описанием, которое FastAPI строит по маршрутам и отдаёт Swagger UI.

    Если маршруты изменились, тест падает. Описание обновляется так:
    ``UPDATE_EXAMPLES=1 uv run pytest Tst/Integration/test_openapi_spec.py``.
    """
    # Подготовка
    spec = app.openapi()
    if os.environ.get(_UPDATE_EXAMPLE_ENV):
        text = yaml.dump(spec, Dumper=_SpecDumper, allow_unicode=True, sort_keys=False, width=120)
        _ = _SPEC_PATH.write_text(text, encoding="utf-8")

    # Действие
    stored = _read_spec()

    # Проверка
    assert stored == spec


# Подготовка
@pytest.mark.parametrize(
    ("path", "methods"),
    [
        ("/api/get_report_formats", {"get"}),
        ("/api/entities/{entity_type}", {"get", "post"}),
        ("/api/entities/{entity_type}/{entity_id}", {"get", "put", "patch", "delete"}),
    ],
    ids=["report_formats", "entity_collection", "entity_item"],
)
def test_openapi_yaml_describes_formats_and_crud_methods(path: str, methods: set[str]):
    """В описании есть метод списка форматов и все CRUD-методы сущностей, у каждого — краткое описание."""
    # Подготовка
    paths = cast(dict[str, dict[str, dict[str, object]]], _read_spec()["paths"])

    # Проверка
    assert set(paths[path]) == methods
    assert all(paths[path][method]["summary"] for method in methods)
