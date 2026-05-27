"""
Upload API.

Pre-upload workflow
-------------------
Files are uploaded BEFORE the user composes a message:

  1. Client POSTs multipart to  POST /api/v1/uploads?room_id=<n>
  2. Server streams file → BlobManager (SHA-256, dedup, persist)
  3. Server persists an Upload DB record (idempotent on hash)
  4. Server enqueues:
       a. ThumbnailJob  — background thumbnail generation
       b. BroadcastJob  — immediate "file_uploaded" WS event (thumbnails_ready=false)
  5. Server returns { blob_hash, file_url, thumbnails, thumbnails_ready=false }
  6. Client stores blob_hash and attaches it when the user hits Send.

When thumbnails finish, the ThumbnailWorker enqueues another BroadcastJob
("thumbnails_ready") so all connected clients update in real-time.

Blob retrieval
--------------
  GET /api/v1/uploads/blob/<blob_hash>    → raw file bytes
  GET /api/v1/uploads/status/<blob_hash>  → Upload record metadata
"""
from __future__ import annotations

import mimetypes
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.upload import Upload
from app.services.thumbnail_service import THUMBNAIL_SIZES
from app.storage.blob_manager import blob_manager
from app.workers.thumbnail import ThumbnailJob, thumbnail_queue

logger = get_logger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ThumbnailURLs(BaseModel):
    sm: str
    md: str
    lg: str


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    blob_hash: str
    original_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    file_url: str
    thumbnails: ThumbnailURLs
    thumbnails_ready: bool
    status: str  # "stored" | "reused"


class UploadStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    blob_hash: str
    original_filename: str
    mime_type: str
    size_bytes: int
    thumbnails_ready: bool
    thumbnails: ThumbnailURLs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _thumbnail_urls(blob_hash: str) -> ThumbnailURLs:
    base = settings.UPLOAD_BASE_URL.rstrip("/")
    return ThumbnailURLs(**{
        label: f"{base}/thumbnails/{blob_hash}_{w}x{h}.jpeg"
        for label, (w, h) in THUMBNAIL_SIZES.items()
    })


def _file_url(blob_hash: str) -> str:
    return f"{settings.UPLOAD_BASE_URL.rstrip('/')}/files/{blob_hash}"


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _build_response(upload: Upload, blob_status: str) -> UploadResponse:
    return UploadResponse(
        blob_hash=upload.hash_id,
        original_filename=upload.original_filename,
        extension=upload.extension,
        mime_type=upload.mime_type,
        size_bytes=upload.size_bytes,
        file_url=_file_url(upload.hash_id),
        thumbnails=_thumbnail_urls(upload.hash_id),
        thumbnails_ready=upload.thumbnails_ready,
        status=blob_status,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    room_id: int = 0,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> UploadResponse:
    """
    Pre-upload a file before attaching it to a message.

    The file is streamed through the BlobManager which computes its SHA-256
    on-the-fly and deduplicates it against already-stored blobs. The Upload
    DB record is created (or re-used if duplicate). A thumbnail job is enqueued
    in the background, and a 'file_uploaded' WebSocket event is broadcast to
    the room immediately — before thumbnails are ready.

    Returns the blob_hash which the client must include when sending the message.
    """
    original_filename = file.filename or "unknown"
    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = _guess_mime(original_filename)

    try:
        blob = await blob_manager.create_blob(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))

    # Idempotent DB record — reuse existing if blob was deduplicated.
    existing_result = await db.execute(select(Upload).where(Upload.hash_id == blob.blob_hash))
    existing: Optional[Upload] = existing_result.scalars().first()

    if existing:
        logger.info("Duplicate upload: hash=%s — returning existing record", blob.blob_hash)
        return _build_response(existing, blob.status)

    # Also save via the legacy backend so static file serving still works.
    from app.storage.backends import storage_backend
    raw_data = await blob_manager.get_blob(blob.blob_hash)
    await storage_backend.save(raw_data, f"files/{blob.blob_hash}")

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

    logger.info(
        "Upload persisted: hash=%s file='%s' backend='%s'",
        blob.blob_hash, original_filename, settings.UPLOAD_BACKEND,
    )

    # Enqueue background thumbnail generation.
    await thumbnail_queue.put(
        ThumbnailJob(
            hash_id=blob.blob_hash,
            file_data=raw_data,
            mime_type=mime_type,
            extension=extension,
            room_id=room_id,
        )
    )

    return _build_response(upload, blob.status)


@router.get("/blob/{blob_hash}", response_class=Response)
async def serve_blob(
    blob_hash: str,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> Response:
    """Serve raw blob bytes. Content-Type is derived from the Upload record."""
    result = await db.execute(select(Upload).where(Upload.hash_id == blob_hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob not found.")

    try:
        data = await blob_manager.get_blob(blob_hash)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob data missing from storage.")

    return Response(content=data, media_type=upload.mime_type)


@router.get("/status/{blob_hash}", response_model=UploadStatusResponse)
async def blob_status(
    blob_hash: str,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> UploadStatusResponse:
    """Return the current DB record for a blob, including thumbnail readiness."""
    result = await db.execute(select(Upload).where(Upload.hash_id == blob_hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob not found.")

    return UploadStatusResponse(
        blob_hash=upload.hash_id,
        original_filename=upload.original_filename,
        mime_type=upload.mime_type,
        size_bytes=upload.size_bytes,
        thumbnails_ready=upload.thumbnails_ready,
        thumbnails=_thumbnail_urls(upload.hash_id),
    )
