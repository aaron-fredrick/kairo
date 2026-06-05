from fastapi import APIRouter, Depends
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/presence", tags=["Presence"])

from app.api.dependencies.auth import get_current_user_id
from app.api.dependencies.services import get_presence_service
from app.schemas.presence_schema import PresenceUpdateResponseSchema, OnlineUsersResponseSchema
from app.application.services.presence_service import PresenceService

@router.post("/heartbeat", response_model=PresenceUpdateResponseSchema)
async def update_presence(
    user_id: int = Depends(get_current_user_id),
    presence_service: PresenceService = Depends(get_presence_service)
):
    """Update presence for a user."""
    timestamp = await presence_service.update_heartbeat(user_id)
    return PresenceUpdateResponseSchema(status="ok", last_seen=timestamp)

@router.get("/online", response_model=OnlineUsersResponseSchema)
async def get_online_users(
    threshold_seconds: int = 60,
    presence_service: PresenceService = Depends(get_presence_service)
):
    """Get users who sent a heartbeat within the threshold."""
    online_users = await presence_service.get_online_users(threshold_seconds)
    return OnlineUsersResponseSchema(online_users=online_users)
