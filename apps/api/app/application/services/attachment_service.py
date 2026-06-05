import structlog
from typing import List

from app.domain.models.attachment_domain import AttachmentDomain
from app.infrastructure.repositories.attachment_repository import AttachmentRepository

logger = structlog.get_logger(__name__)

class AttachmentService:
    def __init__(self, attachment_repo: AttachmentRepository):
        self.attachment_repo = attachment_repo
        
    async def get_attachments(self, message_id: int) -> List[AttachmentDomain]:
        dtos = await self.attachment_repo.get_by_message_id(message_id)
        return [
            AttachmentDomain(
                id=dto.id,
                message_id=dto.message_id,
                upload_id=dto.upload_id,
                filename=dto.filename,
                created_at=dto.created_at,
                updated_at=dto.updated_at
            ) for dto in dtos
        ]
