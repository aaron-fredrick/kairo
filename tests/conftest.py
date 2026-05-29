"""Shared pytest configuration for all packages under tests/."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

_TEST_DB_DIR = Path(__file__).resolve().parent / ".pytest_db"
_TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
_DEFAULT_DB_FILE = _TEST_DB_DIR / "kairo-test.db"

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("SQLITE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_FILE.as_posix()}")
os.environ.setdefault("EVENT_BUS", "local")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-ci-only")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("DATA_DIR", "data/test")

# tests/<package>/<category>/ → pytest markers
_MARKER_BY_DIR = {
    "unit": pytest.mark.unit,
    "component": pytest.mark.component,
    "integration": pytest.mark.integration,
    "regression": pytest.mark.regression,
    "smoke": pytest.mark.smoke,
    "e2e": pytest.mark.e2e,
    "functional": pytest.mark.functional,
    "acceptance": pytest.mark.acceptance,
    "contract": pytest.mark.contract,
    "load": pytest.mark.load,
    "stress": pytest.mark.stress,
    "spike": pytest.mark.spike,
    "soak": pytest.mark.soak,
    "chaos": pytest.mark.chaos,
}

_PRODUCT_BY_DIR = {
    "app_backend": pytest.mark.app_backend,
    "app_register": pytest.mark.app_register,
    "frontend": pytest.mark.frontend,
    "shared": pytest.mark.shared,
}


def _resolve_sqlite_path() -> Path | None:
    url = os.environ.get("SQLITE_URL", "")
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return _DEFAULT_DB_FILE
    path_str = url[len(prefix) :]
    if path_str == ":memory:":
        return None
    return Path(path_str)


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """Create app-backend schema once per session (SQLite file)."""
    import asyncio

    from app_backend.db.database import AsyncSessionLocal, Base, engine
    from app_backend.services.admin_service import admin_service

    async def _setup():
        await engine.dispose()
        db_path = _resolve_sqlite_path()
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if db_path.exists():
                try:
                    db_path.unlink()
                except OSError:
                    pass
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            await admin_service.seed_default_admin(session)
            await admin_service.seed_system_rooms(session)

    asyncio.run(_setup())
    yield
    asyncio.run(engine.dispose())


def pytest_collection_modifyitems(config, items):
    """Apply product + category markers from directory layout."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for dirname, marker in _PRODUCT_BY_DIR.items():
            if dirname in parts:
                item.add_marker(marker)
                break
        for dirname, marker in _MARKER_BY_DIR.items():
            if dirname in parts:
                item.add_marker(marker)
                break


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient for app-backend (session-scoped)."""
    from fastapi.testclient import TestClient

    from app_backend.main import app

    with TestClient(app) as test_client:
        yield test_client
