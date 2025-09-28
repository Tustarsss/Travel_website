"""CLI entrypoint for running the FastAPI application."""

from __future__ import annotations

import uvicorn

from .core import settings


def run() -> None:
    """Start the ASGI server."""

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
