"""Pytest fixtures for backend tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for async tests."""

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Provide the FastAPI application for tests."""

    return create_app()


@pytest.fixture(scope="session")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Return an HTTPX async client bound to the FastAPI app."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
