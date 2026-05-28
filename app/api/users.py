import time
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.auth.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.redis import get_redis
from app.models.user import User

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
    import typing
    pfp_urls = None
    if user.pfp_hash:
        pfp_urls = {
            "128": f"/pfps/{user.pfp_hash}_128.webp",
            "512": f"/pfps/{user.pfp_hash}_512.webp",
            "1024": f"/pfps/{user.pfp_hash}_1024.webp",
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
    redis_client: Redis = Depends(get_redis),
    _: User = Depends(get_current_user),
) -> PresenceResponse:
    """Return currently active users visible in a room (server-wide, capped at 50)."""
    logger.debug("Presence query for room_id=%d", room_id)
    active_users: List[str] = await redis_client.zrangebyscore(
        "active_users",
        min=time.time(),
        max="+inf",
        start=0,
        num=50,
    )
    logger.debug("Found %d active user(s) for presence query", len(active_users))
    return PresenceResponse(room_id=room_id, online_usernames=active_users)
