from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Optional
from app.core.redis import get_redis
import structlog
import time

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/presence", tags=["Presence"])

from app.core.security import get_current_user_id
from app.schemas.presence import PresenceUpdateResponse, OnlineUsersResponse

@router.post("/heartbeat", response_model=PresenceUpdateResponse)
async def update_presence(user_id: int = Depends(get_current_user_id)):
    """
    Update presence for a user.
    Auth lives behind /api, so this assumes the gateway/middleware validates and passes user_id.
    """
    redis = await get_redis()
    timestamp = int(time.time())
    
    try:
        # Update user presence in a Redis sorted set
        await redis.zadd("presence:online_users", {str(user_id): timestamp})
        logger.debug("Presence updated", user_id=user_id)
        return PresenceUpdateResponse(status="ok", last_seen=timestamp)
    except Exception as e:
        logger.error("Failed to update presence", error=str(e))
        raise HTTPException(status_code=500, detail="Could not update presence")

@router.get("/online", response_model=OnlineUsersResponse)
async def get_online_users(threshold_seconds: int = 60):
    """
    Get users who sent a heartbeat within the threshold.
    """
    redis = await get_redis()
    current_time = int(time.time())
    min_score = current_time - threshold_seconds
    
    try:
        # Get users with score >= current_time - threshold
        online_users = await redis.zrangebyscore("presence:online_users", min_score, "+inf")
        return OnlineUsersResponse(online_users=[int(uid) for uid in online_users])
    except Exception as e:
        logger.error("Failed to get online users", error=str(e))
        raise HTTPException(status_code=500, detail="Could not retrieve presence data")
