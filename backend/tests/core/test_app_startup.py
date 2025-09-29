"""Tests covering FastAPI application startup lifecycle."""

from fastapi.testclient import TestClient

from app.core import app as app_module


def test_startup_invokes_database_initialisation(monkeypatch):
    """Ensure the startup hook calls async database initialiser exactly once."""

    calls: list[bool] = []

    async def fake_init_db() -> None:  # pragma: no cover - behaviour under test
        calls.append(True)

    monkeypatch.setattr(app_module, "init_db_async", fake_init_db)

    test_app = app_module.create_app()

    with TestClient(test_app):
        assert calls, "init_db_async should be invoked during application startup"
        assert len(calls) == 1
