from fastapi import APIRouter, Depends, Header
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.services.message_mediator import MessageMediator
from app.schemas.message import MessageWithAttachmentsResponse
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
    logger.info("Fetching message", message_id=message_id, user_id=user_id)
    return await mediator.get_message(message_id)
