from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from pydantic import BaseModel
from typing import List
from app.db.database import get_db
from app.db.redis import get_redis

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

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile():
    """Retrieve profile of the currently logged in user."""
    # TODO: Implement token decoding and database lookup
    return UserProfileResponse(id=1, username="anonymous-fox-123", is_anonymous=True)

@router.get("/presence/{room_id}", response_model=PresenceResponse)
async def get_room_presence(room_id: int, redis_client: Redis = Depends(get_redis)):
    """Fetch all active online users in a specific chat room."""
    # TODO: Query Redis key/value store for active users
    return PresenceResponse(room_id=room_id, online_usernames=["anonymous-fox-123", "swift-otter-456"])
