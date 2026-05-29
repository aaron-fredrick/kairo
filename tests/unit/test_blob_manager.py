"""BlobManager with a local storage provider."""
import pytest

from app.storage.blob_manager import BlobManager
from app.storage.provider import LocalStorageProvider


@pytest.fixture
def blob_mgr(tmp_path):
    return BlobManager(LocalStorageProvider(str(tmp_path)))


@pytest.mark.asyncio
async def test_create_blob_from_bytes(blob_mgr):
    data = b"test-file-content"
    result = await blob_mgr.create_blob_from_bytes(data, mime_type="text/plain")
    assert result.status == "stored"
    assert result.size_bytes == len(data)
    assert len(result.blob_hash) == 64
    assert await blob_mgr.exists(result.blob_hash)


@pytest.mark.asyncio
async def test_create_blob_deduplicates(blob_mgr):
    data = b"duplicate-me"
    first = await blob_mgr.create_blob_from_bytes(data)
    second = await blob_mgr.create_blob_from_bytes(data)
    assert first.blob_hash == second.blob_hash
    assert second.status == "reused"
