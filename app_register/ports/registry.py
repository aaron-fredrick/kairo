"""Registry port — abstract storage for app server records."""
from __future__ import annotations

from typing import Optional, Protocol

from app_register.domain.models import AppServerRecord, RegisterServerInput


class ServerRegistryPort(Protocol):
    """Abstract interface for tracking registered app servers."""

    def register(self, spec: RegisterServerInput) -> AppServerRecord:
        """Register a new app server and return its record (with issued secrets)."""

    def get(self, server_id: str) -> Optional[AppServerRecord]:
        """Return a server by id, or None if unknown."""

    def heartbeat(self, server_id: str) -> Optional[AppServerRecord]:
        """Refresh last-seen time; return None if unknown."""

    def deregister(self, server_id: str) -> bool:
        """Remove a server. Returns False if the id was not found."""

    def list_healthy(self) -> list[AppServerRecord]:
        """Return servers that have not exceeded the heartbeat timeout."""
