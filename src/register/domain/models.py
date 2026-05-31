"""Domain models for the register service."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegisterServerInput:
    """Values supplied by an app server when joining the cluster."""

    host: str
    port: int
    scheme: str = "http"
    hostname: str = ""
    tags: tuple[str, ...] = ("api", "ws")


@dataclass
class AppServerRecord:
    """A registered app server instance tracked by the registry."""

    server_id: str
    upstream: str
    scheme: str
    hostname: str
    tags: list[str]
    heartbeat_secret: str
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

    def is_alive(self, timeout_seconds: float) -> bool:
        return (time.time() - self.last_heartbeat) <= timeout_seconds

    @property
    def upstream_url(self) -> str:
        return f"{self.scheme}://{self.upstream}"
