from fastapi import Depends

from app.dependencies.repositories import (
    get_message_repo_ws,
    get_user_repo_ws,
    get_room_repo_ws,
)
from app.dependencies.container import get_container_ws
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.room_repository import RoomRepository
from app.container import AppContainer


class MessageService:
    """WebSocket message service."""

    def __init__(
        self,
        message_repo: MessageRepository,
        user_repo: UserRepository,
        room_repo: RoomRepository,
        container: AppContainer,
    ):
        self.message_repo = message_repo
        self.user_repo = user_repo
        self.room_repo = room_repo
        self.cache_manager = container.cache_manager
        self.event_manager = container.event_manager

    # TODO: Implement WebSocket message service methods


async def get_ws_message_service(
    message_repo: MessageRepository = Depends(get_message_repo_ws),
    user_repo: UserRepository = Depends(get_user_repo_ws),
    room_repo: RoomRepository = Depends(get_room_repo_ws),
    container: AppContainer = Depends(get_container_ws),
) -> MessageService:
    """Create WebSocket message service instance."""
    return MessageService(
        message_repo=message_repo,
        user_repo=user_repo,
        room_repo=room_repo,
        container=container,
    )
