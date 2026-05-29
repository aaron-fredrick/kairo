"""Shared test environment — must run before app modules are imported by test files."""
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

# Folder name under tests/ → pytest marker (see pytest.ini).
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


def _resolve_sqlite_path() -> Path | None:
    """Return the on-disk SQLite path from SQLITE_URL, or None for :memory:."""
    url = os.environ.get("SQLITE_URL", "")
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return _DEFAULT_DB_FILE
    path_str = url[len(prefix):]
    if path_str == ":memory:":
        return None
    return Path(path_str)


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """Create schema once per session (file-backed SQLite, shared across connections)."""
    import asyncio

    from app.db.database import AsyncSessionLocal, Base, engine
    from app.services.admin_service import admin_service

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
    """Apply markers from tests/<category>/ directory layout."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for dirname, marker in _MARKER_BY_DIR.items():
            if dirname in parts:
                item.add_marker(marker)
                break


@pytest.fixture(scope="session")
def client():
    """Single TestClient for the session — avoids duplicate lifespans/workers."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
