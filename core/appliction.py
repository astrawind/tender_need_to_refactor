from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from v1.bids import router as bids_router
from v1.ping import router as ping_router
from v1.tenders import router as tenders_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tender Management API",
        version="1.0",
        description="API для управления тендерами и предложениями. \n\nОсновные функции API включают управление тендерами (создание, изменение, получение списка) и управление предложениями (создание, изменение, получение списка).\n",
        docs_url="/api/openapi",
        # servers=[
        #     {'url': 'http://localhost:8080/api', 'description': 'Локальный сервер API'}
        # ],
    )

    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(
                {"reason": exc.errors()}
            ),
        )

    app.include_router(ping_router)
    app.include_router(bids_router)
    app.include_router(tenders_router)
    return app
