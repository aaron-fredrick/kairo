"""RegistrationCoordinator unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_register.adapters.memory_registry import InMemoryServerRegistry
from app_register.adapters.proxy.file_publisher import FileProxyPublisher
from app_register.domain.models import RegisterServerInput
from app_register.services.coordinator import RegistrationCoordinator


class _CountingRenderer:
    def __init__(self) -> None:
        self.calls = 0

    def render(self, servers) -> str:
        self.calls += 1
        return f"count={len(servers)}\n"


@pytest.fixture
def coordinator(tmp_path: Path) -> tuple[RegistrationCoordinator, _CountingRenderer]:
    renderer = _CountingRenderer()
    publisher = FileProxyPublisher(
        renderer,
        config_path=str(tmp_path / "out.conf"),
        reload_command="",
    )
    coord = RegistrationCoordinator(
        InMemoryServerRegistry(heartbeat_timeout_seconds=60.0),
        publisher,
        heartbeat_interval_seconds=15,
    )
    return coord, renderer


@pytest.mark.asyncio
async def test_register_publishes_proxy(
    coordinator: tuple[RegistrationCoordinator, _CountingRenderer],
) -> None:
    coord, renderer = coordinator
    record = await coord.register(RegisterServerInput(host="app", port=8000))
    assert record.server_id
    assert renderer.calls >= 1
    assert len(coord.list_healthy()) == 1


@pytest.mark.asyncio
async def test_deregister_publishes_proxy(
    coordinator: tuple[RegistrationCoordinator, _CountingRenderer],
) -> None:
    coord, renderer = coordinator
    record = await coord.register(RegisterServerInput(host="app", port=8000))
    calls_after_register = renderer.calls
    assert await coord.deregister(record.server_id) is True
    assert renderer.calls > calls_after_register
    assert coord.list_healthy() == []
