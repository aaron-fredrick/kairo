from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.message_orm import MessageORM
from app.infrastructure.dtos.message_dto import MessageDTO
from app.infrastructure.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[MessageORM, MessageDTO]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MessageORM, session)

    def _to_dto(self, orm_obj: MessageORM) -> MessageDTO:
        return MessageDTO(
            id=orm_obj.id,
            content=orm_obj.content,
            sender_id=orm_obj.sender_id,
            room_id=orm_obj.room_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
            attachment_ids=[a.id for a in orm_obj.attachments],
        )

    async def get_messages_by_room(
        self, room_id: int, limit: int = 50, offset: int = 0
    ) -> List[MessageDTO]:
        stmt = (
            select(self._model)
            .filter(self._model.room_id == room_id)
            .order_by(self._model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_dto(obj) for obj in result.scalars().all()]
