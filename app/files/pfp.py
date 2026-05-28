import os
import uuid
import shutil
import hashlib
from typing import Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.database import get_db
from app.auth.jwt import get_current_user_payload
from app.models.user import User
from app.core.logging import get_logger
from app.workers.broadcast import broadcast_queue, BroadcastJob
import aiofiles

logger = get_logger(__name__)
router = APIRouter()

TEMP_PFP_DIR = os.path.join(settings.DATA_DIR, "temp", "pfps")
PFP_DIR = os.path.join(settings.DATA_DIR, "pfps")

os.makedirs(TEMP_PFP_DIR, exist_ok=True)
os.makedirs(PFP_DIR, exist_ok=True)


@router.post("/upload/pfp")
async def pre_upload_pfp(
    file: UploadFile = File(...),
    payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """
    Stage a profile picture upload to a temporary directory.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image"
        )

    upload_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_PFP_DIR, upload_id)

    async with aiofiles.open(temp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    return {
        "pfp_upload_id": upload_id,
        "filename": file.filename,
    }


class PfpConfirmRequest(BaseModel):
    pfp_upload_id: str


@router.post("/api/v1/users/me/pfp")
async def confirm_pfp(
    req: PfpConfirmRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """
    Confirm a profile picture, generate 128/512/1024 sizes, update user, and broadcast.
    """
    username = payload.get("sub")
    temp_path = os.path.join(TEMP_PFP_DIR, req.pfp_upload_id)
    if not os.path.exists(temp_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )

    from PIL import Image

    # Read and hash file to generate pfp_hash
    with open(temp_path, "rb") as f:
        file_data = f.read()
    
    pfp_hash = hashlib.sha256(file_data).hexdigest()[:16]

    try:
        with Image.open(temp_path) as img:
            img = img.convert("RGB")

            for size, label in [(128, "128"), (512, "512"), (1024, "1024")]:
                # Simple center crop to square
                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                
                cropped = img.crop((left, top, right, bottom))
                resized = cropped.resize((size, size), Image.Resampling.LANCZOS)
                
                out_path = os.path.join(PFP_DIR, f"{pfp_hash}_{label}.webp")
                resized.save(out_path, "WEBP", quality=85)

    except Exception as e:
        logger.error("Failed to process PFP: %s", e)
        raise HTTPException(status_code=500, detail="Failed to process image")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    # Update user in DB
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.pfp_hash = pfp_hash
    await db.commit()

    # Broadcast pfp_update via WebSocket to all rooms
    from app.models.room import Room
    rooms_result = await db.execute(select(Room))
    all_rooms = rooms_result.scalars().all()

    for r in all_rooms:
        await broadcast_queue.put(
            BroadcastJob(
                room_id=r.id,
                event_type="pfp_updated",
                payload={
                    "username": username,
                    "pfp_hash": pfp_hash,
                    "pfp_urls": {
                        "128": f"/pfps/{pfp_hash}_128.webp",
                        "512": f"/pfps/{pfp_hash}_512.webp",
                        "1024": f"/pfps/{pfp_hash}_1024.webp",
                    }
                },
            )
        )

    return {
        "status": "success",
        "pfp_hash": pfp_hash,
        "pfp_urls": {
            "128": f"/pfps/{pfp_hash}_128.webp",
            "512": f"/pfps/{pfp_hash}_512.webp",
            "1024": f"/pfps/{pfp_hash}_1024.webp",
        }
    }


from fastapi.responses import FileResponse

@router.get("/pfps/{filename}")
async def get_pfp(filename: str):
    """Serve a profile picture file"""
    path = os.path.join(PFP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PFP not found")
    return FileResponse(path, media_type="image/webp")
