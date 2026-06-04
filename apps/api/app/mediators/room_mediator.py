import structlog
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.repositories.room import RoomRepository
from app.schemas.room import RoomResponse

logger = structlog.get_logger(__name__)

class RoomMediator:
    def __init__(self, session: AsyncSession):
        self.room_repo = RoomRepository(session)
        
    async def get_rooms(self) -> List[RoomResponse]:
        rooms = await self.room_repo.get_all()
        return [RoomResponse.model_validate(room) for room in rooms]

    async def get_room(self, room_id: int) -> RoomResponse:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return RoomResponse.model_validate(room)
