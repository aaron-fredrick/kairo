"""Application service — orchestrates registry updates and proxy config publication."""
from __future__ import annotations

from typing import Optional

from app_register.domain.models import AppServerRecord, RegisterServerInput
from app_register.ports.proxy import ProxyConfigPublisher
from app_register.ports.registry import ServerRegistryPort


class RegistrationCoordinator:
    """Coordinates registration lifecycle and reverse-proxy config sync."""

    def __init__(
        self,
        registry: ServerRegistryPort,
        publisher: ProxyConfigPublisher,
        *,
        heartbeat_interval_seconds: int,
    ) -> None:
        self._registry = registry
        self._publisher = publisher
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

    def get(self, server_id: str) -> Optional[AppServerRecord]:
        return self._registry.get(server_id)

    def list_healthy(self) -> list[AppServerRecord]:
        return self._registry.list_healthy()

    async def register(self, spec: RegisterServerInput) -> AppServerRecord:
        record = self._registry.register(spec)
        await self._sync_proxy()
        return record

    async def heartbeat(self, server_id: str) -> Optional[AppServerRecord]:
        record = self._registry.heartbeat(server_id)
        if record is not None:
            await self._sync_proxy()
        return record

    async def deregister(self, server_id: str) -> bool:
        if not self._registry.deregister(server_id):
            return False
        await self._sync_proxy()
        return True

    async def publish_proxy_config(self, servers: list[AppServerRecord] | None = None) -> None:
        """Write proxy config for the given servers, or all healthy servers when omitted."""
        targets = servers if servers is not None else self._registry.list_healthy()
        await self._publisher.publish(targets)

    async def prune_and_sync_if_changed(self) -> bool:
        """Run stale-server prune; republish proxy config if healthy count changed."""
        before = len(self._registry.list_healthy())
        after = len(self._registry.list_healthy())
        if before != after:
            await self._sync_proxy()
            return True
        return False

    async def _sync_proxy(self) -> None:
        await self._publisher.publish(self._registry.list_healthy())
