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
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username, get_current_user_payload
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.upload import Upload
from app.services.thumbnail_service import THUMBNAIL_SIZES
from app.storage.blob_manager import blob_manager

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

    upload_id: str
    original_filename: str
    extension: str
    mime_type: str
    size_bytes: int


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
    # Deprecated for pre-upload. Used for returning status if needed.
    return UploadResponse(
        upload_id="legacy",
        original_filename=upload.original_filename,
        extension=upload.extension,
        mime_type=upload.mime_type,
        size_bytes=upload.size_bytes,
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

    The file is saved to a temporary directory and an `upload_id` is returned.
    It is NOT hashed or stored as a blob yet.
    When the user sends the message, the WS router will process the temp file,
    strip EXIF, hash it, and enqueue thumbnail generation.

    Returns the upload_id which the client must include when sending the message.
    """
    original_filename = file.filename or "unknown"
    _, dot_ext = os.path.splitext(original_filename)
    extension = dot_ext.lstrip(".").lower() or "bin"
    mime_type = _guess_mime(original_filename)

    upload_id = f"upload_{uuid.uuid4().hex}"
    temp_dir = settings.TEMP_UPLOAD_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, upload_id)

    size = 0
    with open(temp_path, "wb") as f:
        while True:
            chunk = await file.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)

    logger.debug("Temp upload saved: %s (%d bytes)", temp_path, size)

    return UploadResponse(
        upload_id=upload_id,
        original_filename=original_filename,
        extension=extension,
        mime_type=mime_type,
        size_bytes=size,
    )


@router.get("/download/{blob_hash}", response_class=Response)
async def download_blob(
    blob_hash: str,
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    """Serve raw blob bytes for download. Authentication is required."""
    result = await db.execute(select(Upload).where(Upload.hash_id == blob_hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob not found.")

    try:
        data = await blob_manager.get_blob(blob_hash)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob data missing from storage.")

    headers = {
        "Content-Disposition": f'attachment; filename="{upload.original_filename}"'
    }
    return Response(content=data, media_type=upload.mime_type, headers=headers)

@router.get("/thumbnails/{blob_hash}", response_class=Response)
async def serve_thumbnail(
    blob_hash: str,
    size: str = "512",
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    """Serve a generated thumbnail image. Authentication is required."""
    if size not in THUMBNAIL_SIZES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid thumbnail size.")
        
    result = await db.execute(select(Upload).where(Upload.hash_id == blob_hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload or not upload.thumbnails_ready:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found or not ready.")

    from app.services.thumbnail_service import thumbnail_abs_path
    import aiofiles

    abs_path = thumbnail_abs_path(blob_hash, size)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file missing from storage.")

    async with aiofiles.open(abs_path, "rb") as fh:
        data = await fh.read()

    return Response(content=data, media_type="image/webp")


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
