"""Storage provider factory."""
from app_backend.storage.provider import LocalStorageProvider, build_storage_provider


def test_build_storage_provider_local():
    p = build_storage_provider("local")
    assert isinstance(p, LocalStorageProvider)


def test_build_storage_provider_unknown_falls_back_local():
    p = build_storage_provider("not-a-real-backend")
    assert isinstance(p, LocalStorageProvider)


def test_build_storage_provider_ftp_falls_back_local():
    p = build_storage_provider("ftp")
    assert isinstance(p, LocalStorageProvider)
