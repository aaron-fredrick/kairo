import hashlib
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app_backend.auth.dependencies import get_current_user
from app_backend.core.logging import get_logger
from app_backend.db.database import get_db
from app_backend.core.state import get_state_manager, StateManager
from app_backend.models.user import User
from app_backend.models.room import Room
from app_backend.workers.broadcast import BroadcastJob, broadcast_queue
from app_backend.storage.paths import pfp_path, temp_pfp_path
from app_backend.storage.provider import get_storage_provider

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
    logger.debug("Presence query for room_id=%d", room_id)
    active_users: List[str] = await state.get_active_users(limit=50)
    logger.debug("Found %d active user(s) for presence query", len(active_users))
    return PresenceResponse(room_id=room_id, online_usernames=active_users)


class PfpConfirmRequest(BaseModel):
    pfp_upload_id: str


def _build_pfp_urls(pfp_hash: str) -> dict:
    return {label: f"/api/data/pfp?hash={pfp_hash}&size={label}" for label in ("128", "512", "1024")}


def _center_crop_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    return img.crop((left, top, left + min_dim, top + min_dim))


def _render_pfp_variants(src_data: bytes) -> dict[str, bytes]:
    """Return size_label → webp bytes for 128/512/1024."""
    with Image.open(io.BytesIO(src_data)) as img:
        img = img.convert("RGB")
        cropped = _center_crop_square(img)
        out: dict[str, bytes] = {}
        for size_str in ("128", "512", "1024"):
            size = int(size_str)
            resized = cropped.resize((size, size), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, "WEBP", quality=85)
            out[size_str] = buf.getvalue()
    return out


@router.post("/me/pfp")
async def confirm_pfp(
    req: PfpConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    provider = get_storage_provider()
    rel = temp_pfp_path(req.pfp_upload_id)

    if not await provider.exists_path(rel):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )

    src_data = await provider.get_path(rel)
    pfp_hash = hashlib.sha256(src_data).hexdigest()[:16]

    try:
        variants = _render_pfp_variants(src_data)
        for size_str, webp_bytes in variants.items():
            await provider.put_path(pfp_path(pfp_hash, size_str), webp_bytes)
    except Exception as e:
        logger.error("Failed to process PFP for '%s': %s", user.username, e)
        raise HTTPException(status_code=500, detail="Failed to process image")
    finally:
        await provider.delete_path(rel)

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
