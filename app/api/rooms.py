import time
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username
from app.core.logging import get_logger
from app.db.database import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    sender_username: str
    room_id: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_username),
) -> RoomResponse:
    """Create a new chat room/channel."""
    logger.debug("Room creation requested by '%s': name='%s'", current_user, room_data.name)
    # TODO: Implement database insertion
    return RoomResponse(
        id=1,
        name=room_data.name,
        description=room_data.description,
        created_at=datetime.utcnow(),
    )


@router.get("/", response_model=List[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_username),
) -> List[RoomResponse]:
    """Return all available rooms."""
    logger.debug("Room list requested by '%s'", current_user)
    # TODO: Implement list retrieval
    return []


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(
    room_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_username),
) -> List[MessageResponse]:
    """Return the message history for a specific room."""
    logger.debug(
        "Message history requested by '%s' for room_id=%d (limit=%d)",
        current_user,
        room_id,
        limit,
    )
    # TODO: Implement historical message query
    return []
