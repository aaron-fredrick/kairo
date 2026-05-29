"""FileProxyPublisher unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_register.adapters.proxy.file_publisher import FileProxyPublisher
from app_register.domain.models import AppServerRecord


class _StubRenderer:
    def render(self, servers: list[AppServerRecord]) -> str:
        return f"servers={len(servers)}\n"


@pytest.mark.asyncio
async def test_publish_writes_config(tmp_path: Path) -> None:
    config_path = tmp_path / "proxy.conf"
    publisher = FileProxyPublisher(
        _StubRenderer(),
        config_path=str(config_path),
        reload_command="",
    )
    record = AppServerRecord(
        server_id="1",
        upstream="h:1",
        scheme="http",
        hostname="h",
        tags=[],
        heartbeat_secret="s",
    )
    await publisher.publish([record])
    assert config_path.read_text(encoding="utf-8") == "servers=1\n"
