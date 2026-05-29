"""Settings helpers."""
from app_backend.core.config import settings


def test_cors_origins_list():
    assert isinstance(settings.cors_origins_list, list)
    assert len(settings.cors_origins_list) >= 1


def test_use_redis_follows_event_bus():
    assert settings.USE_REDIS is (settings.EVENT_BUS == "redis")


def test_ip_lists_empty_by_default():
    assert settings.blacklist_ips == []
    assert settings.whitelist_ips == []
