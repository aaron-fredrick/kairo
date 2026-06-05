import structlog
from typing import List, Optional

from app.core.exceptions import NotFoundError, ForbiddenError
from app.domain.models.attachment_domain import AttachmentDomain
from app.domain.models.message_domain import MessageDomain
from app.domain.policies.message_policy import MessagePolicy
from app.infrastructure.dtos.message_dto import MessageDTO
from app.infrastructure.repositories.attachment_repository import AttachmentRepository
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.cache.cache_manager import CacheManager

logger = structlog.get_logger(__name__)

class MessageService:
    def __init__(self,
                message_repo: MessageRepository,
                attachment_repo: AttachmentRepository,
                message_policy: MessagePolicy,
                cache_manager: CacheManager):
        self.message_repo = message_repo
        self.attachment_repo = attachment_repo
        self.message_policy = message_policy
        self.cache_manager = cache_manager
    
    async def get_message(self, message_id: int, user_id: int) -> MessageDomain:
        # TODO: cache check
        
        message_dto = await self.message_repo.get_by_id(message_id)
        if not message_dto:
            raise NotFoundError()

        attachment_dtos = await self.attachment_repo.get_by_message_id(message_id)
        
        attachment_domains = [
            AttachmentDomain(
                id=a.id,
                message_id=a.message_id,
                upload_id=a.upload_id,
                filename=a.filename,
                created_at=a.created_at,
                updated_at=a.updated_at
            ) for a in attachment_dtos
        ]

        message_domain = MessageDomain(
            id=message_dto.id,
            content=message_dto.content,
            sender_id=message_dto.sender_id,
            room_id=message_dto.room_id,
            created_at=message_dto.created_at,
            updated_at=message_dto.updated_at,
            attachments=attachment_domains
        )

        # Assuming user is member for now, real implementation would check membership
        is_member = True
        if not self.message_policy.can_access(message_domain, user_id, is_member):
            raise ForbiddenError()

        return message_domain
