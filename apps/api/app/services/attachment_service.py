import structlog
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.repositories.message import MessageRepository, AttachmentRepository
from app.schemas.message import MessageCreate, MessageResponse, MessageWithAttachmentsResponse, AttachmentInfo

logger = structlog.get_logger(__name__)

class AttachmentService:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.attachment_repo = AttachmentRepository(session)
        
    async def get_attachments(self, message_id: int):
        return await self.attachment_repo.get_attachments_by_message(message_id)