"""
Upload lifecycle service.

confirm_upload is called from the WebSocket router after a message is saved.
It finalises the staged temp file into a permanent blob and creates an
Attachment row linking the blob to the message.
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
    """
    Finalises a staged temp upload:
    1. Reads the temp file, strips EXIF, and hashes via BlobManager.
    2. Creates (or reuses) the Upload blob record.
    3. Creates an Attachment row linking the blob to the message.
    4. Enqueues thumbnail generation if the blob is new.
    5. Deletes the temp file.

    Returns a tuple containing:
    1. A serialisable attachment dict for the WebSocket broadcast, or None if the temp file is missing.
    2. A ThumbnailJob to be enqueued AFTER the message broadcast, or None.
    """
    temp_path = os.path.join(settings.TEMP_UPLOAD_DIR, upload_id)
    if not os.path.exists(temp_path):
        logger.warning("Temp upload %s not found — skipping.", upload_id)
        return None, None

    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = mime_type or "application/octet-stream"

    # 1. Ingest blob (EXIF-stripped, content-addressed)
    try:
        blob: BlobResult = await blob_manager.create_blob_from_path(temp_path, mime_type=mime_type)
    except ValueError as e:
        logger.error("Upload size exceeded: %s", e)
        return None, None

    # 2. Find or create the Upload (blob) record
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
        await db.flush()   # obtain upload.id without a full commit
        logger.info("Upload blob persisted: hash=%s", blob.blob_hash)
    else:
        logger.info("Reusing existing blob: hash=%s", blob.blob_hash)

    # 3. Create the Attachment row (filename is message-specific)
    attachment = Attachment(
        message_id=message_id,
        upload_id=upload.id,
        filename=original_filename,
    )
    db.add(attachment)
    await db.flush()

    # 4. Prepare thumbnail generation job for new blobs only
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

    # 5. Cleanup temp file
    try:
        os.remove(temp_path)
    except OSError:
        pass

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
