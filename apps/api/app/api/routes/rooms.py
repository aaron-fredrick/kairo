from fastapi import APIRouter, Depends, Header
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.mediators.room_mediator import RoomMediator
from app.mediators.message_mediator import MessageMediator
from app.schemas.room import RoomCreate, RoomResponse
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


# TODO: just a placeholder, implement
@router.post("", response_model=RoomResponse)
async def create_room(
    room_data: RoomCreate,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Create a new room."""
    logger.info("Creating room", user_id=user_id)
    return await mediator.create_room(room_data, user_id)


# TODO: just a placeholder, implement
@router.get("/{room_id}")
async def get_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Get room details."""
    logger.info("Getting room details", room_id=room_id, user_id=user_id)
    return await mediator.get_room(room_id)


# TODO: just a placeholder, implement
@router.get("/{room_id}/join")
async def join_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Join a room."""
    logger.info("Joining room", room_id=room_id, user_id=user_id)
    await mediator.join_room(room_id, user_id)
    return {"message": "Joined room successfully"}


# TODO: just a placeholder, implement
@router.get("/{room_id}/leave")
async def leave_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Leave a room."""
    logger.info("Leaving room", room_id=room_id, user_id=user_id)
    await mediator.leave_room(room_id, user_id)
    return {"message": "Left room successfully"}


# TODO: just a placeholder, implement
@router.post("/{room_id}/add_user")
async def add_user_to_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Add a user to a room."""
    logger.info("Adding user to room", room_id=room_id, user_id=user_id)
    await mediator.add_user_to_room(room_id, user_id)
    return {"message": "User added to room successfully"}


# TODO: just a placeholder, implement
@router.post("/{room_id}/remove_user")
async def remove_user_from_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: RoomMediator = Depends(get_room_mediator)
):
    """Remove a user from a room."""
    logger.info("Removing user from room", room_id=room_id, user_id=user_id)
    await mediator.remove_user_from_room(room_id, user_id)
    return {"message": "User removed from room successfully"}


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
