"""FastAPI application factory."""

from fastapi import FastAPI

from ..api import get_api_router
from .config import settings
from .logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance."""

    configure_logging()

    app = FastAPI(title=settings.project_name, debug=settings.debug)
    app.include_router(get_api_router(), prefix=settings.api_prefix)

    return app
