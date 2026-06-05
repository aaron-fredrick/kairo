from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.dependencies.db import get_db_session
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.attachment_repository import AttachmentRepository
from app.infrastructure.repositories.room_repository import RoomRepository
from app.infrastructure.repositories.user_repository import UserRepository

def get_message_repo(session: AsyncSession = Depends(get_db_session)) -> MessageRepository:
    return MessageRepository(session)

def get_attachment_repo(session: AsyncSession = Depends(get_db_session)) -> AttachmentRepository:
    return AttachmentRepository(session)

def get_room_repo(session: AsyncSession = Depends(get_db_session)) -> RoomRepository:
    return RoomRepository(session)

def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)
