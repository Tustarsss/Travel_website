"""ASGI entrypoint for the Travel Website backend."""

from __future__ import annotations

from fastapi import FastAPI

from .core import create_app


app: FastAPI = create_app()

__all__ = ["app"]
