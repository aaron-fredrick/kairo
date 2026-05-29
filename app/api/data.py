import os
import uuid
import mimetypes
from typing import Any, Dict, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Response, Query
from fastapi.responses import FileResponse
from PIL import Image
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
from app.services.thumbnail_service import THUMBNAIL_SIZES, thumbnail_abs_path

logger = get_logger(__name__)
router = APIRouter(prefix="/data",tags=["data"])

# --- Upload file ---

@router.post("/upload/file", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    room_id: int = 0,
    _payload: dict = Depends(get_current_user_payload),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    upload_id = f"upload_{uuid.uuid4().hex}"
    temp_dir = settings.TEMP_UPLOAD_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, upload_id)

    bytes_written = 0
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024

    try:
        async with aiofiles.open(temp_path, "wb") as f:
            while chunk := await file.read(256 * 1024):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds max size of {settings.UPLOAD_MAX_SIZE_MB}MB",
                    )
                await f.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
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


# --- Upload PFP ---

TEMP_PFP_DIR = os.path.join(settings.DATA_DIR, "temp", "pfps")
os.makedirs(TEMP_PFP_DIR, exist_ok=True)

@router.post("/upload/pfp")
async def upload_pfp(
    file: UploadFile = File(...),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    upload_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_PFP_DIR, upload_id)

    async with aiofiles.open(temp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    return {"pfp_upload_id": upload_id, "filename": file.filename}


# --- Download ---

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


# --- Thumbnails ---

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

    abs_path = thumbnail_abs_path(hash, size)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Thumbnail file missing from storage.")

    async with aiofiles.open(abs_path, "rb") as fh:
        data = await fh.read()

    return Response(content=data, media_type="image/webp")


# --- PFP serve (public) ---

PFP_DIR = os.path.join(settings.DATA_DIR, "pfps")
os.makedirs(PFP_DIR, exist_ok=True)

@router.get("/pfp")
async def serve_pfp(
    hash: str = Query(...),
    size: str = Query("512"),
) -> FileResponse:
    if size not in ("128", "512", "1024"):
        raise HTTPException(status_code=400, detail="Invalid size")
        
    filename = f"{hash}_{size}.webp"
    path = os.path.join(PFP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PFP not found")
    return FileResponse(path, media_type="image/webp")
