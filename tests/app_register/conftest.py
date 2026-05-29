"""app-register test fixtures (component API tests)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app_register.config import RegisterSettings
from app_register.container import build_coordinator, reset_coordinator


@pytest.fixture
def register_client(tmp_path):
    """TestClient wired to an isolated in-memory coordinator."""
    reset_coordinator()
    key = "test-register-system-key"
    os.environ["REGISTER_SYSTEM_KEY"] = key
    cfg = RegisterSettings(
        REGISTER_SYSTEM_KEY=key,
        PROXY_CONFIG_PATH=str(tmp_path / "Caddyfile"),
        PROXY_RELOAD_COMMAND="",
        HEARTBEAT_TIMEOUT_SECONDS=60,
    )
    import app_register.config as register_config
    import app_register.container as container

    register_config.settings = cfg
    container._coordinator = build_coordinator(cfg)
    from app_register.main import app

    with TestClient(app) as client:
        yield client
    reset_coordinator()
