"""
Upload API endpoint.

POST /api/v1/uploads
    - Accepts a multipart file upload (requires valid Bearer token).
    - Computes a SHA-256 hash of the raw bytes; this becomes the hash_id.
    - Saves the file via the configured storage backend (no extension in filename).
    - Persists an Upload record in the database.
    - Returns the file URL, assumed thumbnail URLs, name, extension, and size
      *immediately* — the thumbnail worker runs asynchronously in the background.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.upload import Upload
from app.storage.backends import storage_backend
from app.workers.broadcast import BroadcastJob, broadcast_queue
from app.workers.thumbnail import ThumbnailJob, thumbnail_queue
from app.services.thumbnail_service import THUMBNAIL_SIZES

logger = get_logger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Room ID used when no specific room context is provided — broadcasts to room 0
# so server-wide listeners receive the event.
_GLOBAL_ROOM_ID = 0


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ThumbnailURLs(BaseModel):
    sm: str
    md: str
    lg: str


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hash_id: str
    original_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    file_url: str
    thumbnails: ThumbnailURLs
    thumbnails_ready: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _derive_thumbnail_urls(hash_id: str) -> ThumbnailURLs:
    """
    Return assumed thumbnail URLs for the three standard sizes.
    The actual files may not exist yet if the worker hasn't finished.
    Format: {UPLOAD_BASE_URL}/thumbnails/{hash_id}_{w}x{h}.jpeg
    """
    base = settings.UPLOAD_BASE_URL.rstrip("/")
    urls = {}
    for label, (w, h) in THUMBNAIL_SIZES.items():
        urls[label] = f"{base}/thumbnails/{hash_id}_{w}x{h}.jpeg"
    return ThumbnailURLs(**urls)


def _guess_mime(filename: str, default: str = "application/octet-stream") -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or default


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    room_id: int = 0,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> UploadResponse:
    """
    Accept a file upload, persist it, and return its URLs.

    Pass `room_id` to broadcast the upload event to that room's connected
    WebSocket clients.  Omit it (defaults to 0) for a server-wide broadcast.

    Thumbnail generation happens asynchronously in the background — the
    response is returned immediately with pre-computed (assumed) thumbnail URLs.
    """
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    data = await file.read(max_bytes + 1)

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {settings.UPLOAD_MAX_SIZE_MB} MB.",
        )

    original_filename = file.filename or "unknown"
    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = _guess_mime(original_filename)
    size_bytes = len(data)

    # Derive content-addressed hash_id from the raw file bytes
    hash_id = hashlib.sha256(data).hexdigest()
    file_sha256 = hash_id

    # Idempotency — return existing record if this exact file was already uploaded
    existing_result = await db.execute(select(Upload).where(Upload.hash_id == hash_id))
    existing: Upload | None = existing_result.scalars().first()
    if existing:
        logger.info("Duplicate upload detected for hash_id='%s' — returning existing record", hash_id)
        return _build_response(existing)

    # Persist file bytes (no extension in the stored filename)
    relative_path = f"files/{hash_id}"
    file_url = await storage_backend.save(data, relative_path)

    upload = Upload(
        original_filename=original_filename,
        extension=extension,
        mime_type=mime_type,
        size_bytes=size_bytes,
        hash_id=hash_id,
        storage_backend=settings.UPLOAD_BACKEND,
        storage_path=relative_path,
        file_sha256=file_sha256,
        thumbnails_ready=False,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    logger.info(
        "Upload saved: hash_id='%s', file='%s', backend='%s'",
        hash_id, original_filename, settings.UPLOAD_BACKEND,
    )

    # Enqueue thumbnail generation — fire-and-forget
    await thumbnail_queue.put(
        ThumbnailJob(
            hash_id=hash_id,
            file_data=data,
            mime_type=mime_type,
            extension=extension,
            room_id=room_id,
        )
    )
    logger.debug("Thumbnail job queued for hash_id='%s'", hash_id)

    # Immediately broadcast the upload event so WS clients learn about the file
    # before thumbnails are ready.  room_id=0 signals a server-wide event;
    # callers should pass a room_id query param when a specific room context exists.
    thumb_urls = _derive_thumbnail_urls(hash_id)
    await broadcast_queue.put(
        BroadcastJob(
            room_id=room_id,
            event_type="file_uploaded",
            payload={
                "hash_id": hash_id,
                "filename": original_filename,
                "extension": extension,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "file_url": f"{settings.UPLOAD_BASE_URL.rstrip('/')}/files/{hash_id}",
                "thumbnails": thumb_urls.model_dump(),
                "thumbnails_ready": False,
            },
        )
    )
    logger.debug("Broadcast job queued for hash_id='%s' (file_uploaded)", hash_id)

    return _build_response(upload)


def _build_response(upload: Upload) -> UploadResponse:
    base = settings.UPLOAD_BASE_URL.rstrip("/")
    file_url = f"{base}/files/{upload.hash_id}"
    return UploadResponse(
        hash_id=upload.hash_id,
        original_filename=upload.original_filename,
        extension=upload.extension,
        mime_type=upload.mime_type,
        size_bytes=upload.size_bytes,
        file_url=file_url,
        thumbnails=_derive_thumbnail_urls(upload.hash_id),
        thumbnails_ready=upload.thumbnails_ready,
    )
