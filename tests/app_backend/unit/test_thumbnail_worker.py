"""Thumbnail worker job processing."""
import io

import pytest
from PIL import Image

from app_backend.models.upload import Upload
from app_backend.storage.backends import LocalStorage
from app_backend.workers.thumbnail import ThumbnailJob, _process_job


@pytest.fixture
def storage_provider(tmp_path, monkeypatch):
    import importlib

    from app_backend.storage.blob_manager import BlobManager
    from app_backend.storage.provider import LocalStorageProvider

    prov = LocalStorageProvider(str(tmp_path))
    mgr = BlobManager(prov)
    provider_mod = importlib.import_module("app_backend.storage.provider")
    monkeypatch.setattr(provider_mod, "_provider", prov)
    blob_mod = importlib.import_module("app_backend.storage.blob_manager")
    monkeypatch.setattr(blob_mod, "blob_manager", mgr)
    return prov


@pytest.mark.asyncio
async def test_process_thumbnail_job(storage_provider):
    from app_backend.db.database import AsyncSessionLocal
    from app_backend.storage.blob_manager import blob_manager

    img = Image.new("RGB", (8, 8), color=(1, 2, 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    blob = await blob_manager.create_blob_from_bytes(data, mime_type="image/png")

    async with AsyncSessionLocal() as db:
        upload = Upload(
            original_filename="x.png",
            extension="png",
            mime_type="image/png",
            size_bytes=len(data),
            hash_id=blob.blob_hash,
            storage_backend="local",
            storage_path=blob.storage_path,
            file_sha256=blob.blob_hash,
            thumbnails_ready=False,
        )
        db.add(upload)
        await db.commit()

    job = ThumbnailJob(
        hash_id=blob.blob_hash,
        file_data=data,
        mime_type="image/png",
        extension="png",
        room_id=1,
    )
    await _process_job(job, LocalStorage())

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        row = (await db.execute(select(Upload).where(Upload.hash_id == blob.blob_hash))).scalars().one()
        assert row.thumbnails_ready is True
