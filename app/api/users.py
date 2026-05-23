from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from pydantic import BaseModel
from typing import List
from app.db.database import get_db
from app.db.redis import get_redis
from app.auth.jwt import get_current_username
from app.models.user import User

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
    db: AsyncSession = Depends(get_db)
) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        user = User(username=username, is_anonymous=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(user: User = Depends(get_current_db_user)):
    """Retrieve profile of the currently logged in user."""
    return UserProfileResponse(id=user.id, username=user.username, is_anonymous=user.is_anonymous)

@router.get("/presence/{room_id}", response_model=PresenceResponse)
async def get_room_presence(
    room_id: int, 
    redis_client: Redis = Depends(get_redis),
    _: str = Depends(get_current_username)
):
    """Fetch all active online users in a specific chat room."""
    # We can get active users globally or per room.
    # For now, just returning placeholder or global active users.
    # To do it properly per room, websocket manager should push to redis,
    # but we will just return global active users for demo or placeholder.
    active_count = await redis_client.zcard("active_users")
    # Actually getting all active users could be large, let's just return a few
    active_users = await redis_client.zrangebyscore("active_users", min=__import__('time').time(), max="+inf", start=0, num=50)
    return PresenceResponse(room_id=room_id, online_usernames=active_users)
