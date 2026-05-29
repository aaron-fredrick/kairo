import uuid
import mimetypes
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Response, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user_payload
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.attachment import Attachment
from app.models.upload import Upload
from app.storage.blob_manager import blob_manager
from app.services.thumbnail_service import THUMBNAIL_SIZES
from app.storage.paths import pfp_path, temp_pfp_path, temp_upload_path, thumbnail_path
from app.storage.provider import get_storage_provider

logger = get_logger(__name__)
router = APIRouter(prefix="/data", tags=["data"])


@router.post("/upload/file", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    room_id: int = 0,
    _payload: dict = Depends(get_current_user_payload),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    upload_id = f"upload_{uuid.uuid4().hex}"
    provider = get_storage_provider()
    rel = temp_upload_path(upload_id)

    chunks: list[bytes] = []
    bytes_written = 0
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024

    try:
        while chunk := await file.read(256 * 1024):
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds max size of {settings.UPLOAD_MAX_SIZE_MB}MB",
                )
            chunks.append(chunk)
        await provider.put_path(rel, b"".join(chunks))
    except HTTPException:
        await provider.delete_path(rel)
        raise
    except Exception as e:
        await provider.delete_path(rel)
        raise HTTPException(status_code=500, detail=str(e))

    mime_type = file.content_type
    if not mime_type or mime_type == "application/octet-stream":
        mime_type, _ = mimetypes.guess_type(file.filename)
        mime_type = mime_type or "application/octet-stream"

    return {
        "upload_id": upload_id,
        "original_filename": file.filename,
        "mime_type": mime_type,
        "size_bytes": bytes_written,
        "room_id": room_id,
    }


@router.post("/upload/pfp")
async def upload_pfp(
    file: UploadFile = File(...),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    upload_id = str(uuid.uuid4())
    provider = get_storage_provider()
    rel = temp_pfp_path(upload_id)

    chunks: list[bytes] = []
    while chunk := await file.read(1024 * 1024):
        chunks.append(chunk)
    await provider.put_path(rel, b"".join(chunks))

    return {"pfp_upload_id": upload_id, "filename": file.filename}


@router.get("/download", response_class=Response)
async def download_file(
    attachment_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    result = await db.execute(
        select(Attachment)
        .options(joinedload(Attachment.upload))
        .where(Attachment.id == attachment_id)
    )
    attachment: Optional[Attachment] = result.scalars().first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    upload = attachment.upload
    try:
        data = await blob_manager.get_blob(upload.hash_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Blob data missing from storage.")

    headers = {
        "Content-Disposition": f'attachment; filename="{attachment.filename}"'
    }
    return Response(content=data, media_type=upload.mime_type, headers=headers)


@router.get("/thumbnails", response_class=Response)
async def serve_thumbnail(
    hash: str = Query(...),
    size: str = Query("512"),
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    if size not in THUMBNAIL_SIZES:
        raise HTTPException(status_code=400, detail="Invalid thumbnail size.")

    result = await db.execute(select(Upload).where(Upload.hash_id == hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload or not upload.thumbnails_ready:
        raise HTTPException(status_code=404, detail="Thumbnail not found or not ready.")

    provider = get_storage_provider()
    rel = thumbnail_path(hash, size)
    try:
        data = await provider.get_path(rel)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Thumbnail file missing from storage.")

    return Response(content=data, media_type="image/webp")


@router.get("/pfp")
async def serve_pfp(
    hash: str = Query(...),
    size: str = Query("512"),
) -> Response:
    if size not in ("128", "512", "1024"):
        raise HTTPException(status_code=400, detail="Invalid size")

    provider = get_storage_provider()
    rel = pfp_path(hash, size)
    try:
        data = await provider.get_path(rel)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PFP not found")
    return Response(content=data, media_type="image/webp")
