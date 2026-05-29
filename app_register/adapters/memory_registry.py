"""In-memory implementation of ServerRegistryPort."""
from __future__ import annotations

import secrets
import time
import uuid
from typing import Optional

from app_register.domain.models import AppServerRecord, RegisterServerInput
from app_register.ports.registry import ServerRegistryPort


class InMemoryServerRegistry(ServerRegistryPort):
    def __init__(
        self,
        *,
        heartbeat_timeout_seconds: float,
        prune_multiplier: float = 2.0,
    ) -> None:
        self._heartbeat_timeout = heartbeat_timeout_seconds
        self._prune_multiplier = prune_multiplier
        self._servers: dict[str, AppServerRecord] = {}

    def register(self, spec: RegisterServerInput) -> AppServerRecord:
        server_id = str(uuid.uuid4())
        upstream = f"{spec.host}:{spec.port}"
        record = AppServerRecord(
            server_id=server_id,
            upstream=upstream,
            scheme=spec.scheme,
            hostname=spec.hostname or upstream,
            tags=list(spec.tags),
            heartbeat_secret=secrets.token_urlsafe(32),
        )
        self._servers[server_id] = record
        return record

    def get(self, server_id: str) -> Optional[AppServerRecord]:
        return self._servers.get(server_id)

    def heartbeat(self, server_id: str) -> Optional[AppServerRecord]:
        record = self._servers.get(server_id)
        if record is None:
            return None
        record.last_heartbeat = time.time()
        return record

    def deregister(self, server_id: str) -> bool:
        return self._servers.pop(server_id, None) is not None

    def list_healthy(self) -> list[AppServerRecord]:
        self._prune_stale()
        return [s for s in self._servers.values() if s.is_alive(self._heartbeat_timeout)]

    def _prune_stale(self) -> None:
        threshold = self._heartbeat_timeout * self._prune_multiplier
        dead = [
            sid
            for sid, s in self._servers.items()
            if not s.is_alive(self._heartbeat_timeout)
            and (time.time() - s.last_heartbeat) > threshold
        ]
        for sid in dead:
            del self._servers[sid]
