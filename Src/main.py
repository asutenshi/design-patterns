import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.abstract_report_result import AbstractReportResult
from Src.Core.entity_type import EntityType
from Src.Core.exception import ArgumentsException, OperationException
from Src.Core.named_entity import NamedEntity
from Src.Core.response_format import ResponseFormat
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


app = FastAPI(title="Ромашка", description="Автоматизация сети ресторанов «Ромашка»", lifespan=lifespan)


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


def _report_response(result: AbstractReportResult, file_stem: str) -> Response:
    """Превращает результат отчёта в HTTP-ответ.

    Двоичный результат (``is_binary``) отдаётся файлом на скачивание: байты и заголовок
    ``Content-Disposition: attachment``. Остальные — текстом с MIME-типом формата.

    :param result: Результат отчёта.
    :param file_stem: Имя файла без расширения, только ASCII: так его не нужно кодировать в заголовке.
    :return: Ответ с содержимым отчёта.
    """
    if not result.is_binary:
        return Response(content=result.text, media_type=result.media_type)

    file_name = f"{file_stem}.{result.file_extension}"
    return Response(
        content=result.binary,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


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

# Параметры пути, общие для отчётов по сущности
EntityTypePath = Annotated[EntityType, Path(description="Тип сущности: номенклатура, единица измерения или рецепт")]
EntityIdPath = Annotated[uuid.UUID, Path(description="Код (идентификатор) сущности")]


@app.get("/api/reports/{response_format}/{entity_type}/{entity_id}", response_class=Response, responses=_REPORT_RESPONSES)
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
    result = factory.create(response_format).build(entity)
    return _report_response(result, f"{entity_type.value}-{entity.id}")


@app.get("/api/reports/{entity_type}/{entity_id}", response_class=Response, responses=_REPORT_RESPONSES)
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
    result = factory.create_default().build(entity)
    return _report_response(result, f"{entity_type.value}-{entity.id}")


@app.get("/api/get_report", response_class=Response, responses={404: {"description": "Карта не найдена"}})
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
    return _report_response(report.build(recipe), f"{EntityType.RECIPE.value}-{recipe.id}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
