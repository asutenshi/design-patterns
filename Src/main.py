from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from Src.Core.abstract_report_factory import AbstractReportFactory
from Src.Core.exception import ArgumentsException, OperationException
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
    """Зависимость маршрутов: фабрика отчётов."""
    return ReportFactory()


@app.exception_handler(ArgumentsException)
async def handle_arguments_exception(_: Request, ex: ArgumentsException) -> JSONResponse:
    """Превращает ошибку некорректного аргумента в ответ 400."""
    return JSONResponse(status_code=400, content={"detail": str(ex)})


@app.exception_handler(OperationException)
async def handle_operation_exception(_: Request, ex: OperationException) -> JSONResponse:
    """Превращает ошибку выполнения операции в ответ 500."""
    return JSONResponse(status_code=500, content={"detail": str(ex)})


@app.get("/api/get_report", response_class=Response, responses={404: {"description": "Карта не найдена"}})
def get_report(
    recipe_name: Annotated[str, Query(description="Наименование карты, регистр не учитывается")],
    storage: Annotated[StorageManager, Depends(get_storage)],
    factory: Annotated[AbstractReportFactory, Depends(get_report_factory)],
    response_format: Annotated[ResponseFormat, Query(description="Формат отчёта")] = ResponseFormat.TXT,
) -> Response:
    """Формирует отчёт по технологической карте в указанном формате.

    :param recipe_name: Наименование карты, регистр и пробелы по краям не учитываются.
    :param storage: Хранилище, в котором ищется карта.
    :param factory: Фабрика, создающая отчёт нужного формата.
    :param response_format: Формат отчёта, по умолчанию TXT.
    :return: Содержимое отчёта с MIME-типом формата.
    :raises HTTPException: 404, если карты с таким наименованием нет.
    """
    recipe = storage.find_recipe_by_name(recipe_name)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Технологическая карта «{recipe_name}» не найдена")

    result = factory.create(response_format).build(recipe)
    return Response(content=result.binary, media_type=result.media_type)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
