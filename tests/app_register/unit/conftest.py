"""Shared fixtures for register unit tests."""
from __future__ import annotations

import time

import pytest

from app_register.domain.models import AppServerRecord, RegisterServerInput


@pytest.fixture
def sample_record() -> AppServerRecord:
    return AppServerRecord(
        server_id="srv-1",
        upstream="app:8000",
        scheme="http",
        hostname="app",
        tags=["api", "ws"],
        heartbeat_secret="hb-secret",
        last_heartbeat=time.time(),
    )


@pytest.fixture
def sample_input() -> RegisterServerInput:
    return RegisterServerInput(host="app", port=8000, hostname="worker-1")
