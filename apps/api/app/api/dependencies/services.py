from fastapi import Depends
from app.api.dependencies.container import get_container
from app.container import AppContainer

from app.application.services.message_service import MessageService
from app.application.services.attachment_service import AttachmentService
from app.application.services.presence_service import PresenceService

from app.api.dependencies.repositories import get_message_repo, get_attachment_repo
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.attachment_repository import AttachmentRepository
from app.domain.policies.message_policy import MessagePolicy

def get_message_policy() -> MessagePolicy:
    return MessagePolicy()

def get_message_service(
    message_repo: MessageRepository = Depends(get_message_repo),
    attachment_repo: AttachmentRepository = Depends(get_attachment_repo),
    message_policy: MessagePolicy = Depends(get_message_policy),
    container: AppContainer = Depends(get_container)
) -> MessageService:
    return MessageService(
        message_repo=message_repo,
        attachment_repo=attachment_repo,
        message_policy=message_policy,
        cache_manager=container.cache_manager
    )

def get_attachment_service(
    attachment_repo: AttachmentRepository = Depends(get_attachment_repo)
) -> AttachmentService:
    return AttachmentService(attachment_repo=attachment_repo)

def get_presence_service(
    container: AppContainer = Depends(get_container)
) -> PresenceService:
    return PresenceService(cache_manager=container.cache_manager)
