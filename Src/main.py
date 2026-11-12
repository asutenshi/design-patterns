import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, cast

import uvicorn
from fastapi import (
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)
from fastapi.openapi.models import Example
from fastapi.responses import JSONResponse
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.entity_type import EntityType
from Src.Core.exception import (
    ArgumentsException,
    OperationException,
    ReferencedEntityException,
)
from Src.Core.named_entity import NamedEntity
from Src.Core.response_format import ResponseFormat
from Src.Logics.converter_factory import ConverterFactory
from Src.Logics.report_factory import ReportFactory
from Src.Logics.settings_manager import SettingsManager
from Src.Logics.storage_manager import StorageManager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Загружает настройки и хранилище при старте приложения.

    Уже загруженные менеджеры не перезагружаются: так тесты и другой код запуска
    могут подготовить их заранее, например загрузить настройки из своего файла.
    """
    settings_manager = SettingsManager()
    if not settings_manager.is_loaded:
        settings_manager.load()
    storage = StorageManager()
    if not storage.is_loaded:
        storage.load(settings_manager)
    yield


# Группы маршрутов в Swagger
_REPORTS_TAG = "Отчёты"
_ENTITIES_TAG = "Сущности"

app = FastAPI(
    title="Ромашка",
    description="Автоматизация сети ресторанов «Ромашка»",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": _REPORTS_TAG, "description": "Отчёты по сущностям в разных форматах"},
        {"name": _ENTITIES_TAG, "description": "Создание, чтение, изменение и удаление доменных сущностей"},
    ],
)


def get_storage() -> StorageManager:
    """Зависимость маршрутов: хранилище доменных моделей."""
    return StorageManager()


def get_report_factory() -> AbstractReportFactory:
    """Зависимость маршрутов: фабрика отчётов с текущими настройками приложения."""
    return ReportFactory(SettingsManager().settings)


@app.exception_handler(ArgumentsException)
async def handle_arguments_exception(_: Request, ex: ArgumentsException) -> JSONResponse:
    """Превращает ошибку некорректного аргумента в ответ 400."""
    return JSONResponse(status_code=400, content={"detail": str(ex)})


@app.exception_handler(OperationException)
async def handle_operation_exception(_: Request, ex: OperationException) -> JSONResponse:
    """Превращает ошибку выполнения операции в ответ 500."""
    return JSONResponse(status_code=500, content={"detail": str(ex)})


@app.exception_handler(ReferencedEntityException)
async def handle_referenced_entity_exception(_: Request, ex: ReferencedEntityException) -> JSONResponse:
    """Превращает запрет удалить или перекодировать связанную сущность в ответ 409 со списком ссылающихся."""
    return JSONResponse(status_code=409, content={"detail": str(ex), "referrers": list(ex.referrers)})


def _find_entity(storage: StorageManager, entity_type: EntityType, entity_id: uuid.UUID) -> NamedEntity:
    """Возвращает сущность из хранилища по типу и коду.

    :param storage: Хранилище, в котором ищется сущность.
    :param entity_type: Тип сущности.
    :param entity_id: Код сущности.
    :return: Найденная сущность.
    :raises HTTPException: 404, если сущности такого типа с таким кодом нет.
    """
    entity = storage.find(entity_type, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Сущность {entity_type.value} с кодом {entity_id} не найдена")
    return entity


# Описание ответов отчёта для Swagger: тело зависит от формата, поэтому схема JSON не подходит
_REPORT_RESPONSES: dict[int | str, dict[str, str]] = {
    200: {"description": "Отчёт: Markdown и CSV — файлом на скачивание, остальные форматы — текстом"},
    404: {"description": "Сущность не найдена"},
}

# Параметры пути, общие для отчётов и CRUD по сущности
EntityTypePath = Annotated[
    EntityType, Path(description="Тип сущности: номенклатура, группа номенклатуры, единица измерения, склад или рецепт")
]
EntityIdPath = Annotated[uuid.UUID, Path(description="Код (идентификатор) сущности")]


@app.get(
    "/api/reports/{response_format}/{entity_type}/{entity_id}",
    summary="Отчёт по сущности в указанном формате",
    response_class=Response,
    responses=_REPORT_RESPONSES,
    tags=[_REPORTS_TAG],
)
def get_entity_report(
    response_format: Annotated[ResponseFormat, Path(description="Формат отчёта")],
    entity_type: EntityTypePath,
    entity_id: EntityIdPath,
    storage: Annotated[StorageManager, Depends(get_storage)],
    factory: Annotated[AbstractReportFactory, Depends(get_report_factory)],
) -> Response:
    """Формирует отчёт по сущности указанного типа и кода в указанном формате.

    :param response_format: Формат отчёта.
    :param entity_type: Тип сущности.
    :param entity_id: Код сущности.
    :param storage: Хранилище, в котором ищется сущность.
    :param factory: Фабрика, создающая отчёт нужного формата.
    :return: Содержимое отчёта: Markdown и CSV — файлом, остальные форматы — текстом.
    :raises HTTPException: 404, если сущности нет.
    """
    entity = _find_entity(storage, entity_type, entity_id)
    return factory.create(response_format).build(entity).to_response(f"{entity_type.value}-{entity.id}")


@app.get(
    "/api/reports/{entity_type}/{entity_id}",
    summary="Отчёт по сущности в формате из настроек",
    response_class=Response,
    responses=_REPORT_RESPONSES,
    tags=[_REPORTS_TAG],
)
def get_entity_default_report(
    entity_type: EntityTypePath,
    entity_id: EntityIdPath,
    storage: Annotated[StorageManager, Depends(get_storage)],
    factory: Annotated[AbstractReportFactory, Depends(get_report_factory)],
) -> Response:
    """Формирует отчёт по сущности указанного типа и кода в формате из настроек (``create_default``).

    :param entity_type: Тип сущности.
    :param entity_id: Код сущности.
    :param storage: Хранилище, в котором ищется сущность.
    :param factory: Фабрика, создающая отчёт в формате из настроек.
    :return: Содержимое отчёта: Markdown и CSV — файлом, остальные форматы — текстом.
    :raises HTTPException: 404, если сущности нет.
    """
    entity = _find_entity(storage, entity_type, entity_id)
    return factory.create_default().build(entity).to_response(f"{entity_type.value}-{entity.id}")


@app.get(
    "/api/get_report",
    summary="Отчёт по технологической карте по наименованию",
    response_class=Response,
    responses={404: {"description": "Карта не найдена"}},
    tags=[_REPORTS_TAG],
)
def get_report(
    recipe_name: Annotated[str, Query(description="Наименование карты, регистр не учитывается")],
    storage: Annotated[StorageManager, Depends(get_storage)],
    factory: Annotated[AbstractReportFactory, Depends(get_report_factory)],
    response_format: Annotated[ResponseFormat | None, Query(description="Формат отчёта, по умолчанию из настроек")] = None,
) -> Response:
    """Формирует отчёт по технологической карте в указанном формате.

    :param recipe_name: Наименование карты, регистр и пробелы по краям не учитываются.
    :param storage: Хранилище, в котором ищется карта.
    :param factory: Фабрика, создающая отчёт нужного формата.
    :param response_format: Формат отчёта, None — формат из настроек.
    :return: Содержимое отчёта: Markdown и CSV — файлом, остальные форматы — текстом.
    :raises HTTPException: 404, если карты с таким наименованием нет.
    """
    recipe = storage.find_recipe_by_name(recipe_name)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Технологическая карта «{recipe_name}» не найдена")

    report = factory.create_default() if response_format is None else factory.create(response_format)
    return report.build(recipe).to_response(f"{EntityType.RECIPE.value}-{recipe.id}")


@app.get("/api/get_report_formats", summary="Форматы отчётов", tags=[_REPORTS_TAG])
def get_report_formats() -> list[ResponseFormat]:
    """Возвращает все форматы, в которых можно построить отчёт.

    Список берётся из перечисления ``ResponseFormat``: новый формат появляется здесь без правки маршрута.

    :return: Значения форматов в порядке объявления, например ``["txt", "markdown", ...]``.
    """
    return list(ResponseFormat)


# Ответы с ошибками, общие для маршрутов, которые меняют сущность
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, str]] = {404: {"description": "Сущность не найдена"}}
_INVALID_DATA_RESPONSE: dict[int | str, dict[str, str]] = {
    400: {"description": "Некорректные данные, ссылка на неизвестную сущность, занятые код или наименование"},
}
_REFERENCED_RESPONSE: dict[int | str, dict[str, str]] = {
    409: {"description": "На сущность ссылаются другие сущности: удалять её и менять код нельзя"},
}

# Пример кода сущности в примерах тела запроса: вместо него подставляется код из хранилища
_EXAMPLE_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

# Примеры тела запроса для Swagger: по одному на каждый вид данных
_ENTITY_EXAMPLES: dict[str, Example] = {
    "warehouse": {
        "summary": "Склад или группа номенклатуры",
        "value": {"name": "Склад №3"},
    },
    "range": {
        "summary": "Единица измерения",
        "description": "Производная единица ссылается на базовую по коду; у базовой ``base`` равен null.",
        "value": {"name": "центнер", "factor": 100000, "base": {"id": _EXAMPLE_ID}},
    },
    "nomenclature": {
        "summary": "Номенклатура",
        "description": "Группа и единица измерения задаются ссылками на сущности хранилища.",
        "value": {
            "name": "Пастернак",
            "full_name": "Пастернак корневой",
            "group": {"id": _EXAMPLE_ID},
            "range": {"id": _EXAMPLE_ID},
            "type": "сырьё",
            "grams_per_base_unit": 1,
        },
    },
}

# Тело запроса: поля сущности в формате выгрузки (ConverterFactory)
EntityBody = Annotated[
    dict[str, object],
    Body(
        description=(
            "Поля сущности в формате выгрузки. Вложенные сущности хранилища задаются ссылкой "
            '``{"id": "<код>"}``, ``model_type`` у самой сущности можно не указывать.'
        ),
        openapi_examples=_ENTITY_EXAMPLES,
    ),
]


def _to_json(entity: NamedEntity) -> dict[str, object]:
    """Превращает сущность в словарь для ответа так же, как её выгружает хранилище.

    :param entity: Сущность хранилища.
    :return: Поля сущности в формате выгрузки.
    """
    return cast(dict[str, object], ConverterFactory().convert(entity))


@app.get("/api/entities/{entity_type}", summary="Список сущностей типа", tags=[_ENTITIES_TAG])
def get_entities(
    entity_type: EntityTypePath, storage: Annotated[StorageManager, Depends(get_storage)]
) -> list[dict[str, object]]:
    """Возвращает все сущности указанного типа.

    :param entity_type: Тип сущности.
    :param storage: Хранилище сущностей.
    :return: Сущности в формате выгрузки, в порядке добавления.
    """
    return [_to_json(entity) for entity in storage.entities(entity_type)]


@app.get(
    "/api/entities/{entity_type}/{entity_id}",
    summary="Сущность по коду",
    tags=[_ENTITIES_TAG],
    responses=_NOT_FOUND_RESPONSE,
)
def get_entity(
    entity_type: EntityTypePath, entity_id: EntityIdPath, storage: Annotated[StorageManager, Depends(get_storage)]
) -> dict[str, object]:
    """Возвращает сущность указанного типа по коду.

    :param entity_type: Тип сущности.
    :param entity_id: Код сущности.
    :param storage: Хранилище сущностей.
    :return: Сущность в формате выгрузки.
    :raises HTTPException: 404, если сущности нет.
    """
    return _to_json(_find_entity(storage, entity_type, entity_id))


@app.post(
    "/api/entities/{entity_type}",
    summary="Создать сущность",
    status_code=201,
    tags=[_ENTITIES_TAG],
    responses=_INVALID_DATA_RESPONSE,
)
def create_entity(
    entity_type: EntityTypePath, data: EntityBody, storage: Annotated[StorageManager, Depends(get_storage)]
) -> dict[str, object]:
    """Создаёт сущность указанного типа.

    Если в данных есть ``id``, он становится кодом сущности, иначе код создаётся автоматически.

    :param entity_type: Тип сущности.
    :param data: Поля сущности.
    :param storage: Хранилище сущностей.
    :return: Созданная сущность в формате выгрузки.
    """
    return _to_json(storage.create(entity_type, data))


@app.put(
    "/api/entities/{entity_type}/{entity_id}",
    summary="Заменить все поля сущности",
    tags=[_ENTITIES_TAG],
    responses={**_INVALID_DATA_RESPONSE, **_NOT_FOUND_RESPONSE, **_REFERENCED_RESPONSE},
)
def put_entity(
    entity_type: EntityTypePath,
    entity_id: EntityIdPath,
    data: EntityBody,
    storage: Annotated[StorageManager, Depends(get_storage)],
) -> dict[str, object]:
    """Полностью заменяет поля сущности: поля, которых нет в данных, не сохраняются.

    Без ``id`` в данных код не меняется. Другой ``id`` меняет код, но только у сущности,
    на которую никто не ссылается.

    :param entity_type: Тип сущности.
    :param entity_id: Текущий код сущности.
    :param data: Все поля сущности.
    :param storage: Хранилище сущностей.
    :return: Изменённая сущность в формате выгрузки.
    :raises HTTPException: 404, если сущности нет.
    """
    _ = _find_entity(storage, entity_type, entity_id)
    return _to_json(storage.put(entity_type, entity_id, data))


@app.patch(
    "/api/entities/{entity_type}/{entity_id}",
    summary="Изменить часть полей сущности",
    tags=[_ENTITIES_TAG],
    responses={**_INVALID_DATA_RESPONSE, **_NOT_FOUND_RESPONSE, **_REFERENCED_RESPONSE},
)
def patch_entity(
    entity_type: EntityTypePath,
    entity_id: EntityIdPath,
    data: EntityBody,
    storage: Annotated[StorageManager, Depends(get_storage)],
) -> dict[str, object]:
    """Изменяет только указанные поля сущности, остальные сохраняются.

    Значение поля заменяется целиком, в том числе вложенный объект. Код меняется по тем же правилам, что у PUT.

    :param entity_type: Тип сущности.
    :param entity_id: Текущий код сущности.
    :param data: Изменяемые поля сущности.
    :param storage: Хранилище сущностей.
    :return: Изменённая сущность в формате выгрузки.
    :raises HTTPException: 404, если сущности нет.
    """
    _ = _find_entity(storage, entity_type, entity_id)
    return _to_json(storage.patch(entity_type, entity_id, data))


@app.delete(
    "/api/entities/{entity_type}/{entity_id}",
    summary="Удалить сущность",
    status_code=204,
    tags=[_ENTITIES_TAG],
    responses={**_NOT_FOUND_RESPONSE, **_REFERENCED_RESPONSE},
)
def delete_entity(
    entity_type: EntityTypePath, entity_id: EntityIdPath, storage: Annotated[StorageManager, Depends(get_storage)]
) -> None:
    """Удаляет сущность, если на неё никто не ссылается.

    :param entity_type: Тип сущности.
    :param entity_id: Код сущности.
    :param storage: Хранилище сущностей.
    :raises HTTPException: 404, если сущности нет.
    """
    _ = _find_entity(storage, entity_type, entity_id)
    storage.delete(entity_type, entity_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
