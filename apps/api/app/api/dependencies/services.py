from fastapi import Depends
from app.api.dependencies.container import get_container
from app.container import AppContainer

from app.application.services.message_service import MessageService
from app.application.services.attachment_service import AttachmentService
from app.application.services.presence_service import PresenceService

from app.api.dependencies.repositories import get_message_repo, get_attachment_repo, get_upload_repo, get_user_repo
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.attachment_repository import AttachmentRepository
from app.infrastructure.repositories.upload_repository import UploadRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.domain.policies.message_policy import MessagePolicy
from app.infrastructure.storage.storage_client import get_storage_client, StorageClient
from app.infrastructure.events.local_event_manager import LocalEventManager
from app.application.services.auth_service import AuthService

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    container: AppContainer = Depends(get_container)
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        cache_manager=container.cache_manager,
        event_manager=container.event_manager
    )

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
    attachment_repo: AttachmentRepository = Depends(get_attachment_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    upload_repo: UploadRepository = Depends(get_upload_repo),
    message_policy: MessagePolicy = Depends(get_message_policy),
    storage_client: StorageClient = Depends(get_storage_client),
    container: AppContainer = Depends(get_container)
) -> AttachmentService:
    return AttachmentService(
        attachment_repo=attachment_repo,
        message_repo=message_repo,
        upload_repo=upload_repo,
        cache_manager=container.cache_manager,
        storage_client=storage_client,
        message_policy=message_policy,
        event_protocol=container.event_manager
    )

def get_presence_service(
    container: AppContainer = Depends(get_container)
) -> PresenceService:
    return PresenceService(cache_manager=container.cache_manager)
