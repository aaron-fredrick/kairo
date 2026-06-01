from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.repositories.base import BaseRepository
from app.models.message import Message
from app.models.attachment import Attachment

class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_messages_by_room(self, room_id: int, limit: int = 50, offset: int = 0) -> List[Message]:
        stmt = select(self.model).filter(self.model.room_id == room_id).order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Attachment, session)
        
    async def get_attachments_by_message(self, message_id: int) -> List[Attachment]:
        stmt = select(self.model).filter(self.model.message_id == message_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
