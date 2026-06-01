import structlog
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.repositories.message import MessageRepository, AttachmentRepository
from app.schemas.message import MessageCreate, MessageResponse, MessageWithAttachmentsResponse, AttachmentInfo

logger = structlog.get_logger(__name__)

class MessageMediator:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.attachment_repo = AttachmentRepository(session)
        
    async def get_room_messages(self, room_id: int, limit: int = 50, offset: int = 0) -> List[MessageWithAttachmentsResponse]:
        messages = await self.message_repo.get_messages_by_room(room_id, limit, offset)
        
        response_list = []
        for msg in messages:
            # We would typically do a joinedload or eager load here, but keeping it simple
            attachments = await self.attachment_repo.get_attachments_by_message(msg.id)
            att_info = [
                AttachmentInfo(
                    id=att.id,
                    filename=att.filename,
                    content_type=att.content_type,
                    size=att.size,
                    url=None # Would be resolved via upload_mediator or pre-signed URL system if requested
                ) for att in attachments
            ]
            response_list.append(
                MessageWithAttachmentsResponse(
                    id=msg.id,
                    content=msg.content,
                    room_id=msg.room_id,
                    sender_id=msg.sender_id,
                    created_at=msg.created_at,
                    updated_at=msg.updated_at,
                    attachments=att_info
                )
            )
        
        return response_list

    async def get_message(self, message_id: int) -> MessageWithAttachmentsResponse:
        msg = await self.message_repo.get_by_id(message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
            
        attachments = await self.attachment_repo.get_attachments_by_message(msg.id)
        att_info = [
            AttachmentInfo(
                id=att.id,
                filename=att.filename,
                content_type=att.content_type,
                size=att.size,
                url=None
            ) for att in attachments
        ]
        
        return MessageWithAttachmentsResponse(
            id=msg.id,
            content=msg.content,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            attachments=att_info
        )
