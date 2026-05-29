"""Upload confirm pipeline."""
import io

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.message import Message
from app.models.user import User
from app.services.upload_service import confirm_upload
from app.storage.paths import temp_upload_path
from app.storage.provider import LocalStorageProvider


@pytest.fixture
def storage_provider(tmp_path, monkeypatch):
    import importlib

    from app.storage.blob_manager import BlobManager

    prov = LocalStorageProvider(str(tmp_path))
    mgr = BlobManager(prov)
    provider_mod = importlib.import_module("app.storage.provider")
    blob_mod = importlib.import_module("app.storage.blob_manager")
    upload_mod = importlib.import_module("app.services.upload_service")
    monkeypatch.setattr(provider_mod, "_provider", prov)
    monkeypatch.setattr(blob_mod, "blob_manager", mgr)
    monkeypatch.setattr(upload_mod, "blob_manager", mgr)
    return prov


@pytest.mark.asyncio
async def test_confirm_upload_creates_attachment(storage_provider):
    from app.db.database import AsyncSessionLocal

    img = Image.new("RGB", (10, 10), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    upload_id = "upload_test_confirm"
    await storage_provider.put_path(temp_upload_path(upload_id), buf.getvalue())

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalars().first()
        msg = Message(content="", sender_id=user.id, room_id=1)
        db.add(msg)
        await db.flush()

        result, job = await confirm_upload(
            upload_id=upload_id,
            original_filename="shot.png",
            mime_type="image/png",
            size_bytes=len(buf.getvalue()),
            message_id=msg.id,
            room_id=1,
            db=db,
        )
        await db.commit()

    assert result is not None
    assert result["filename"] == "shot.png"
    assert job is not None
    assert not await storage_provider.exists_path(temp_upload_path(upload_id))
