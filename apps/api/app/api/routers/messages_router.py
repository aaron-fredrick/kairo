from fastapi import APIRouter, Depends
import structlog

from app.api.dependencies.auth import get_current_user_id
from app.api.dependencies.services import get_message_service
from app.schemas.message_schema import MessageWithAttachmentsResponseSchema

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("/{message_id}", response_model=MessageWithAttachmentsResponseSchema)
async def get_message(
    message_id: int,
    user_id: int = Depends(get_current_user_id),
    service = Depends(get_message_service)
):
    # Call service
    domain_obj = await service.get_message(message_id, user_id)
    # Mapping domain to schema in real code here
    # For now return stub or empty dict because response_model needs it
    # Pydantic will complain if not right type, so returning dict that matches
    return {
        "id": domain_obj.id,
        "content": domain_obj.content,
        "sender_id": domain_obj.sender_id,
        "room_id": domain_obj.room_id,
        "created_at": domain_obj.created_at,
        "updated_at": domain_obj.updated_at,
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "content_type": "application/octet-stream", # Stubbed because domain doesn't track it yet, usually joined
                "size": 0,
                "url": None
            } for a in domain_obj.attachments
        ]
    }