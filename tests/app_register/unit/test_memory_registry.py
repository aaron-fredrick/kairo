"""InMemoryServerRegistry unit tests."""
from __future__ import annotations

import time

from app_register.adapters.memory_registry import InMemoryServerRegistry
from app_register.domain.models import RegisterServerInput


def test_register_and_get(sample_input: RegisterServerInput) -> None:
    registry = InMemoryServerRegistry(heartbeat_timeout_seconds=30.0)
    record = registry.register(sample_input)
    assert record.server_id
    assert record.upstream == "app:8000"
    assert record.heartbeat_secret
    assert registry.get(record.server_id) is record


def test_heartbeat_updates_timestamp(sample_input: RegisterServerInput) -> None:
    registry = InMemoryServerRegistry(heartbeat_timeout_seconds=30.0)
    record = registry.register(sample_input)
    old = record.last_heartbeat
    time.sleep(0.01)
    updated = registry.heartbeat(record.server_id)
    assert updated is not None
    assert updated.last_heartbeat > old


def test_list_healthy_excludes_stale(sample_input: RegisterServerInput) -> None:
    registry = InMemoryServerRegistry(heartbeat_timeout_seconds=0.05, prune_multiplier=1.0)
    record = registry.register(sample_input)
    time.sleep(0.1)
    healthy = registry.list_healthy()
    assert record.server_id not in {s.server_id for s in healthy}


def test_deregister(sample_input: RegisterServerInput) -> None:
    registry = InMemoryServerRegistry(heartbeat_timeout_seconds=30.0)
    record = registry.register(sample_input)
    assert registry.deregister(record.server_id) is True
    assert registry.get(record.server_id) is None
    assert registry.deregister(record.server_id) is False
