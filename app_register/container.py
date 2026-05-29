"""Dependency wiring for the register service."""
from __future__ import annotations

from app_register.adapters.memory_registry import InMemoryServerRegistry
from app_register.adapters.proxy.factory import build_proxy_publisher
from app_register.config import RegisterSettings, settings
from app_register.services.coordinator import RegistrationCoordinator

_coordinator: RegistrationCoordinator | None = None


def build_coordinator(cfg: RegisterSettings | None = None) -> RegistrationCoordinator:
    cfg = cfg or settings
    registry = InMemoryServerRegistry(
        heartbeat_timeout_seconds=float(cfg.HEARTBEAT_TIMEOUT_SECONDS),
    )
    publisher = build_proxy_publisher(cfg)
    return RegistrationCoordinator(
        registry,
        publisher,
        heartbeat_interval_seconds=cfg.HEARTBEAT_INTERVAL_SECONDS,
    )


def get_coordinator() -> RegistrationCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = build_coordinator()
    return _coordinator


def reset_coordinator() -> None:
    """Clear the singleton coordinator (used in tests)."""
    global _coordinator
    _coordinator = None
