import hashlib
import os
import uuid
from typing import Any, Dict

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user_payload
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.room import Room
from app.models.user import User
from app.workers.broadcast import BroadcastJob, broadcast_queue

logger = get_logger(__name__)
router = APIRouter()

TEMP_PFP_DIR = os.path.join(settings.DATA_DIR, "temp", "pfps")
PFP_DIR = os.path.join(settings.DATA_DIR, "pfps")

os.makedirs(TEMP_PFP_DIR, exist_ok=True)
os.makedirs(PFP_DIR, exist_ok=True)

_PFP_SIZES = [(128, "128"), (512, "512"), (1024, "1024")]


def _build_pfp_urls(pfp_hash: str) -> Dict[str, str]:
    return {label: f"/pfps/{pfp_hash}_{label}.webp" for _, label in _PFP_SIZES}


def _center_crop_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    return img.crop((left, top, left + min_dim, top + min_dim))


def _process_and_save_pfp(src_path: str, pfp_hash: str) -> None:
    """Open, crop, resize and save PFP at all three resolutions."""
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        cropped = _center_crop_square(img)
        for size, label in _PFP_SIZES:
            resized = cropped.resize((size, size), Image.Resampling.LANCZOS)
            out_path = os.path.join(PFP_DIR, f"{pfp_hash}_{label}.webp")
            resized.save(out_path, "WEBP", quality=85)


@router.post("/upload/pfp")
async def pre_upload_pfp(
    file: UploadFile = File(...),
    payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Stage a profile picture upload to a temporary directory."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image"
        )

    upload_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_PFP_DIR, upload_id)

    async with aiofiles.open(temp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    return {"pfp_upload_id": upload_id, "filename": file.filename}


class PfpConfirmRequest(BaseModel):
    pfp_upload_id: str


@router.post("/api/v1/users/me/pfp")
async def confirm_pfp(
    req: PfpConfirmRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Confirm a PFP upload, generate 128/512/1024 thumbnails, update user, and broadcast."""
    username = payload.get("sub")
    temp_path = os.path.join(TEMP_PFP_DIR, req.pfp_upload_id)

    if not os.path.exists(temp_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )

    with open(temp_path, "rb") as f:
        pfp_hash = hashlib.sha256(f.read()).hexdigest()[:16]

    try:
        _process_and_save_pfp(temp_path, pfp_hash)
    except Exception as e:
        logger.error("Failed to process PFP for '%s': %s", username, e)
        raise HTTPException(status_code=500, detail="Failed to process image")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.pfp_hash = pfp_hash
    await db.commit()

    pfp_urls = _build_pfp_urls(pfp_hash)

    rooms_result = await db.execute(select(Room))
    for r in rooms_result.scalars().all():
        await broadcast_queue.put(
            BroadcastJob(
                room_id=r.id,
                event_type="pfp_updated",
                payload={"username": username, "pfp_hash": pfp_hash, "pfp_urls": pfp_urls},
            )
        )

    return {"status": "success", "pfp_hash": pfp_hash, "pfp_urls": pfp_urls}


@router.get("/pfps/{filename}")
async def get_pfp(filename: str) -> FileResponse:
    """Serve a profile picture file."""
    path = os.path.join(PFP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PFP not found")
    return FileResponse(path, media_type="image/webp")
