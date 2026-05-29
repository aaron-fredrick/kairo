"""Local storage provider and path helpers."""
import pytest

from app_backend.storage.paths import (
    normalize_posix_path,
    pfp_path,
    temp_pfp_path,
    temp_upload_path,
    thumbnail_path,
)
from app_backend.storage.provider import LocalStorageProvider


@pytest.fixture
def provider(tmp_path):
    return LocalStorageProvider(str(tmp_path))


@pytest.mark.asyncio
async def test_put_get_exists_delete_path(provider):
    rel = "temp/uploads/stage-1"
    await provider.put_path(rel, b"payload")
    assert await provider.exists_path(rel)
    assert await provider.get_path(rel) == b"payload"
    await provider.delete_path(rel)
    assert not await provider.exists_path(rel)
    await provider.delete_path(rel)  # no-op


@pytest.mark.asyncio
async def test_content_addressed_blob(provider):
    digest = "ab" * 32
    await provider.put(digest, b"blob-bytes")
    assert await provider.exists(digest)
    assert await provider.get(digest) == b"blob-bytes"
    await provider.delete(digest)
    assert not await provider.exists(digest)


@pytest.mark.asyncio
async def test_get_missing_raises(provider):
    with pytest.raises(FileNotFoundError):
        await provider.get_path("missing/object")


def test_path_helpers():
    assert normalize_posix_path("a\\b/c") == "a/b/c"
    assert temp_upload_path("u") == "temp/uploads/u"
    assert temp_pfp_path("p") == "temp/pfps/p"
    h = "f" * 64
    assert thumbnail_path(h, "512").endswith(f"{h}_512.webp")
    assert pfp_path("abc", "128") == "pfps/abc_128.webp"
