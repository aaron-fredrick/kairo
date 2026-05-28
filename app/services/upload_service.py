"""
Upload lifecycle service.
"""
from __future__ import annotations

import mimetypes
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.upload import Upload
from app.storage.blob_manager import BlobResult, blob_manager
from app.services.thumbnail_service import THUMBNAIL_SIZES, thumbnail_url
from app.workers.thumbnail import ThumbnailJob, thumbnail_queue

logger = get_logger(__name__)


async def confirm_upload(
    upload_id: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    room_id: int,
    db: AsyncSession,
) -> dict:
    """
    Confirms an upload staged in the temp directory.
    - Hashes and strips EXIF via BlobManager.
    - Creates or re-uses the Upload DB record.
    - Enqueues a thumbnail job.
    - Deletes the temp file.
    - Returns the attachment dictionary for the WS broadcast.
    """
    temp_path = os.path.join(settings.TEMP_UPLOAD_DIR, upload_id)
    if not os.path.exists(temp_path):
        logger.warning("Temp upload %s missing.", temp_path)
        return {}

    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = mime_type or "application/octet-stream"

    # 1. Ingest via BlobManager (this strips EXIF for images and hashes)
    try:
        blob: BlobResult = await blob_manager.create_blob_from_path(temp_path, mime_type=mime_type)
    except ValueError as e:
        logger.error("Upload size exceeded: %s", e)
        return {}

    # 2. Check for duplicate DB record
    existing_result = await db.execute(select(Upload).where(Upload.hash_id == blob.blob_hash))
    upload: Optional[Upload] = existing_result.scalars().first()

    if not upload:
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
        await db.commit()
        await db.refresh(upload)

        logger.info("Upload persisted: hash=%s", blob.blob_hash)

        # Enqueue thumbnail generation for the new blob
        # We need the raw bytes for the thumbnail worker.
        raw_data = await blob_manager.get_blob(blob.blob_hash)
        await thumbnail_queue.put(
            ThumbnailJob(
                hash_id=blob.blob_hash,
                file_data=raw_data,
                mime_type=mime_type,
                extension=extension,
                room_id=room_id,
            )
        )
    else:
        logger.info("Duplicate upload reused: hash=%s", blob.blob_hash)

    # 3. Cleanup temp file
    try:
        os.remove(temp_path)
    except OSError:
        pass

    # 4. Return metadata for WS broadcast
    base = settings.API_BASE_URL.rstrip("/")
    return {
        "blob_hash": blob.blob_hash,
        "filename": upload.original_filename,
        "mime_type": upload.mime_type,
        "size_bytes": upload.size_bytes,
        "file_url": f"{base}/uploads/download/{blob.blob_hash}",
        "thumbnails": {
            label: thumbnail_url(blob.blob_hash, label)
            for label in THUMBNAIL_SIZES.keys()
        },
        "thumbnails_ready": upload.thumbnails_ready,
    }
