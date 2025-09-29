"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..api import get_api_router
from .config import settings
from .db import init_db_async
from .logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance."""

    configure_logging()

    app = FastAPI(title=settings.project_name, debug=settings.debug)

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("startup")
    async def _ensure_database() -> None:
        await init_db_async()

    app.include_router(get_api_router(), prefix=settings.api_prefix)

    return app
