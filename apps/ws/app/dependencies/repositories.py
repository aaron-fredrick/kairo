from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.dependencies.db import get_db_session
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.room_repository import RoomRepository


def get_message_repo_ws(session: AsyncSession = Depends(get_db_session)) -> MessageRepository:
    """WebSocket dependency for message repository."""
    return MessageRepository(session)


def get_user_repo_ws(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """WebSocket dependency for user repository."""
    return UserRepository(session)


def get_room_repo_ws(session: AsyncSession = Depends(get_db_session)) -> RoomRepository:
    """WebSocket dependency for room repository."""
    return RoomRepository(session)
