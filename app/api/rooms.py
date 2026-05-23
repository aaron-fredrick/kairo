from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db

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
async def create_room(room_data: RoomCreate, db: AsyncSession = Depends(get_db)):
    """Create a new chat room/channel."""
    # TODO: Implement database insertion
    return RoomResponse(
        id=1, 
        name=room_data.name, 
        description=room_data.description, 
        created_at=datetime.utcnow()
    )

@router.get("/", response_model=List[RoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    """Fetch all available rooms."""
    # TODO: Implement list retrieval
    return []

@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_messages(room_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Fetch message history for a specific room."""
    # TODO: Implement historical message query
    return []
