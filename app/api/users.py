import time
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.redis import get_redis
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    id: int
    username: str
    is_anonymous: bool

    class Config:
        from_attributes = True


class PresenceResponse(BaseModel):
    room_id: int
    online_usernames: List[str]


async def get_current_db_user(
    username: str = Depends(get_current_username),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that resolves the authenticated username to a User ORM
    instance, creating a new anonymous record if the user has not been seen before.
    """
    result = await db.execute(select(User).where(User.username == username))
    user: User | None = result.scalars().first()

    if not user:
        logger.info("First-time user '%s' — creating DB record", username)
        user = User(username=username, is_anonymous=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        logger.debug("Resolved user '%s' (id=%d)", username, user.id)

    return user


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_db_user),
) -> UserProfileResponse:
    """Return the profile of the currently authenticated user."""
    logger.debug("Profile requested by '%s'", user.username)
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        is_anonymous=user.is_anonymous,
    )


@router.get("/presence/{room_id}", response_model=PresenceResponse)
async def get_room_presence(
    room_id: int,
    redis_client: Redis = Depends(get_redis),
    _: str = Depends(get_current_username),
) -> PresenceResponse:
    """Return the list of currently active users (server-wide, capped at 50)."""
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
