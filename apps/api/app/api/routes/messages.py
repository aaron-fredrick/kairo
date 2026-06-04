from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.mediators.message_mediator import MessageMediator
from app.schemas.message import AttachmentInfo, MessageWithAttachmentsResponse
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/messages", tags=["Messages"])

def get_message_mediator(session: AsyncSession = Depends(get_db_session)) -> MessageMediator:
    return MessageMediator(session)

from app.core.security import get_current_user_id

@router.get("/{message_id}", response_model=MessageWithAttachmentsResponse)
async def get_message(
    message_id: int,
    user_id: int = Depends(get_current_user_id),
    mediator: MessageMediator = Depends(get_message_mediator)
):
    """Get a specific message and its attachments info."""
    result = await mediator.get_message(message_id)

    if not result:
        raise HTTPException(status_code=404, detail="Message not found")

    msg, attachments = result

    att_info = [
        AttachmentInfo(
            id=att.id,
            filename=att.filename,
            content_type=att.content_type,
            size=att.size,
            url=None
        )
        for att in attachments
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
