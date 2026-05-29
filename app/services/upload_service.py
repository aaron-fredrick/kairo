"""
Upload lifecycle service.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.attachment import Attachment
from app.models.upload import Upload
from app.services.thumbnail_service import THUMBNAIL_SIZES, thumbnail_url
from app.storage.blob_manager import BlobResult, blob_manager
from app.storage.paths import temp_upload_path
from app.storage.provider import get_storage_provider
from app.workers.thumbnail import ThumbnailJob

logger = get_logger(__name__)


async def confirm_upload(
    upload_id: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    message_id: int,
    room_id: int,
    db: AsyncSession,
) -> Tuple[Optional[dict], Optional[ThumbnailJob]]:
    provider = get_storage_provider()
    rel = temp_upload_path(upload_id)
    if not await provider.exists_path(rel):
        logger.warning("Temp upload %s not found — skipping.", upload_id)
        return None, None

    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = mime_type or "application/octet-stream"

    try:
        data = await provider.get_path(rel)
        blob: BlobResult = await blob_manager.create_blob_from_bytes(data, mime_type=mime_type)
    except ValueError as e:
        logger.error("Upload size exceeded: %s", e)
        return None, None

    existing = await db.execute(select(Upload).where(Upload.hash_id == blob.blob_hash))
    upload: Optional[Upload] = existing.scalars().first()
    is_new_blob = upload is None

    if is_new_blob:
        upload = Upload(
            original_filename=original_filename,
            extension=extension,
            mime_type=mime_type,
            size_bytes=blob.size_bytes,
            hash_id=blob.blob_hash,
            storage_backend=settings.UPLOAD_BACKEND,
            storage_path=blob.storage_path,
            file_sha256=blob.blob_hash,
            thumbnails_ready=False,
        )
        db.add(upload)
        await db.flush()
        logger.info("Upload blob persisted: hash=%s", blob.blob_hash)
    else:
        logger.info("Reusing existing blob: hash=%s", blob.blob_hash)

    attachment = Attachment(
        message_id=message_id,
        upload_id=upload.id,
        filename=original_filename,
    )
    db.add(attachment)
    await db.flush()

    job = None
    if is_new_blob:
        raw_data = await blob_manager.get_blob(blob.blob_hash)
        job = ThumbnailJob(
            hash_id=blob.blob_hash,
            file_data=raw_data,
            mime_type=mime_type,
            extension=extension,
            room_id=room_id,
        )

    await provider.delete_path(rel)

    return {
        "attachment_id": attachment.id,
        "blob_hash": blob.blob_hash,
        "filename": attachment.filename,
        "mime_type": upload.mime_type,
        "size_bytes": upload.size_bytes,
        "file_url": f"/api/data/download?attachment_id={attachment.id}",
        "thumbnails": {
            label: thumbnail_url(blob.blob_hash, label)
            for label in THUMBNAIL_SIZES.keys()
        },
        "thumbnails_ready": upload.thumbnails_ready,
    }, job
