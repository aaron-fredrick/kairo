import time
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.auth.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.database import get_db
from app.core.state import get_state_manager, StateManager
from app.models.user import User
from app.models.room import Room
from app.workers.broadcast import BroadcastJob, broadcast_queue
from app.core.config import settings

import os
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    id: int
    username: str
    role: str
    is_anonymous: bool
    pfp_urls: Optional[dict] = None

    class Config:
        from_attributes = True


class PresenceResponse(BaseModel):
    room_id: int
    online_usernames: List[str]


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Return the profile of the currently authenticated user."""
    logger.debug("Profile requested by '%s'", user.username)
    pfp_urls = None
    if user.pfp_hash:
        pfp_urls = {
            "128": f"/api/data/pfp?hash={user.pfp_hash}&size=128",
            "512": f"/api/data/pfp?hash={user.pfp_hash}&size=512",
            "1024": f"/api/data/pfp?hash={user.pfp_hash}&size=1024",
        }
        
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_anonymous=user.is_anonymous,
        pfp_urls=pfp_urls,
    )


@router.get("/presence/{room_id}", response_model=PresenceResponse)
async def get_room_presence(
    room_id: int,
    state: StateManager = Depends(get_state_manager),
    _: User = Depends(get_current_user),
) -> PresenceResponse:
    """Return currently active users visible in a room (server-wide, capped at 50)."""
    logger.debug("Presence query for room_id=%d", room_id)
    active_users: List[str] = await state.get_active_users(limit=50)
    logger.debug("Found %d active user(s) for presence query", len(active_users))
    return PresenceResponse(room_id=room_id, online_usernames=active_users)


# --- PFP Confirmation ---

TEMP_PFP_DIR = os.path.join(settings.DATA_DIR, "temp", "pfps")
PFP_DIR = os.path.join(settings.DATA_DIR, "pfps")

class PfpConfirmRequest(BaseModel):
    pfp_upload_id: str

def _build_pfp_urls(pfp_hash: str) -> dict:
    return {label: f"/api/data/pfp?hash={pfp_hash}&size={label}" for label in ("128", "512", "1024")}

def _center_crop_square(img) -> Any:
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    return img.crop((left, top, left + min_dim, top + min_dim))

def _process_and_save_pfp(src_path: str, pfp_hash: str) -> None:
    from PIL import Image
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        cropped = _center_crop_square(img)
        for size_str in ("128", "512", "1024"):
            size = int(size_str)
            resized = cropped.resize((size, size), Image.Resampling.LANCZOS)
            out_path = os.path.join(PFP_DIR, f"{pfp_hash}_{size_str}.webp")
            resized.save(out_path, "WEBP", quality=85)

@router.post("/me/pfp")
async def confirm_pfp(
    req: PfpConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Confirm a PFP upload, generate thumbnails, update user, and broadcast."""
    temp_path = os.path.join(TEMP_PFP_DIR, req.pfp_upload_id)

    if not os.path.exists(temp_path):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )

    with open(temp_path, "rb") as f:
        pfp_hash = hashlib.sha256(f.read()).hexdigest()[:16]

    try:
        _process_and_save_pfp(temp_path, pfp_hash)
    except Exception as e:
        logger.error("Failed to process PFP for '%s': %s", user.username, e)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to process image")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    user.pfp_hash = pfp_hash
    await db.commit()

    pfp_urls = _build_pfp_urls(pfp_hash)

    rooms_result = await db.execute(select(Room))
    for r in rooms_result.scalars().all():
        await broadcast_queue.put(
            BroadcastJob(
                room_id=r.id,
                event_type="pfp_updated",
                payload={"username": user.username, "pfp_hash": pfp_hash, "pfp_urls": pfp_urls},
            )
        )

    return {"status": "success", "pfp_hash": pfp_hash, "pfp_urls": pfp_urls}
