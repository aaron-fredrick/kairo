import structlog
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.repositories.message import MessageRepository, AttachmentRepository

from app.models.message import Message
from app.models.attachment import Attachment

logger = structlog.get_logger(__name__)

class MessageService:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.attachment_repo = AttachmentRepository(session)
        
    async def get_message_with_attachments(self, message_id: int) -> Optional[tuple[Message, List[Attachment]]]:
        msg = await self.message_repo.get_by_id(message_id)

        if not msg:
            return None
        
        attachments = await self.attachment_repo.get_attachments_by_message(message_id)

        return msg, attachments