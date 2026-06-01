from fastapi import APIRouter, Depends, Header
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.services.room_mediator import RoomMediator
from app.services.message_mediator import MessageMediator
from app.schemas.room import RoomResponse
from app.schemas.message import MessageWithAttachmentsResponse
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/rooms", tags=["Rooms"])

def get_room_mediator(session: AsyncSession = Depends(get_db_session)) -> RoomMediator:
    return RoomMediator(session)

def get_message_mediator(session: AsyncSession = Depends(get_db_session)) -> MessageMediator:
    return MessageMediator(session)

from app.core.security import get_current_user_id

@router.get("", response_model=List[RoomResponse])
async def list_rooms(
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """List all rooms."""
    logger.info("Listing rooms", user_id=user_id)
    return await mediator.get_rooms()

@router.get("/{room_id}/messages", response_model=List[MessageWithAttachmentsResponse])
async def get_room_messages(
    room_id: int,
    limit: int = 50,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    mediator: MessageMediator = Depends(get_message_mediator)
):
    """Get message list for a room, including attachment info."""
    logger.info("Fetching room messages", room_id=room_id, user_id=user_id, limit=limit, offset=offset)
    return await mediator.get_room_messages(room_id, limit, offset)
