from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.attachment_orm import AttachmentORM
from app.infrastructure.dtos.attachment_dto import AttachmentDTO
from app.infrastructure.repositories.base_repository import BaseRepository


class AttachmentRepository(BaseRepository[AttachmentORM, AttachmentDTO]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AttachmentORM, session)

    def _to_dto(self, orm_obj: AttachmentORM) -> AttachmentDTO:
        return AttachmentDTO(
            id=orm_obj.id,
            message_id=orm_obj.message_id,
            upload_id=orm_obj.upload_id,
            filename=orm_obj.filename,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    async def get_by_message_id(self, message_id: int) -> List[AttachmentDTO]:
        stmt = select(self._model).filter(self._model.message_id == message_id)
        result = await self._session.execute(stmt)
        return [self._to_dto(obj) for obj in result.scalars().all()]
