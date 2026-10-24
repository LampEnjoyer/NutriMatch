import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import router as v1_router
from app.config import get_settings
from app.pricing.kroger import KrogerError

logger = logging.getLogger("nutrimatch")


def create_app() -> FastAPI:
    app = FastAPI(title="NutriMatch API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # Log the real error; don't leak SQL or connection details to the client.
        logger.exception("Database error", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "Database error. Please try again."})

    @app.exception_handler(KrogerError)
    async def kroger_error_handler(_request: Request, exc: KrogerError) -> JSONResponse:
        logger.warning("Kroger API error: %s (status %s)", exc.message, exc.status_code)
        return JSONResponse(status_code=502, content={"detail": exc.message})

    app.include_router(v1_router)
    return app


app = create_app()
