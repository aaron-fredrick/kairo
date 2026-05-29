"""Proxy configuration ports."""
from __future__ import annotations

from typing import Protocol

from app_register.domain.models import AppServerRecord


class ProxyConfigRenderer(Protocol):
    """Renders load-balancer configuration text from healthy upstreams."""

    def render(self, servers: list[AppServerRecord]) -> str:
        ...


class ProxyConfigPublisher(Protocol):
    """Writes configuration and optionally reloads the reverse proxy."""

    async def publish(self, servers: list[AppServerRecord]) -> None:
        ...
