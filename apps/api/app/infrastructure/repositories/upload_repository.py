from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.upload_orm import UploadORM
from app.infrastructure.dtos.upload_dto import UploadDTO
from app.infrastructure.repositories.base_repository import BaseRepository


class UploadRepository(BaseRepository[UploadORM, UploadDTO]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UploadORM, session)

    def _to_dto(self, orm_obj: UploadORM) -> UploadDTO:
        return UploadDTO(
            id=orm_obj.id,
            original_filename=orm_obj.original_filename,
            extension=orm_obj.extension,
            mime_type=orm_obj.mime_type,
            size_bytes=orm_obj.size_bytes,
            hash_id=orm_obj.hash_id,
            storage_backend=orm_obj.storage_backend,
            storage_path=orm_obj.storage_path,
            file_sha256=orm_obj.file_sha256,
            thumbnails_ready=orm_obj.thumbnails_ready,
            thumbnail_sha256_sm=orm_obj.thumbnail_sha256_sm,
            thumbnail_sha256_md=orm_obj.thumbnail_sha256_md,
            thumbnail_sha256_lg=orm_obj.thumbnail_sha256_lg,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    async def get_by_hash(self, file_sha256: str) -> Optional[UploadDTO]:
        """Get upload by file hash for deduplication."""
        stmt = select(self._model).filter(self._model.file_sha256 == file_sha256)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_dto(orm_obj) if orm_obj else None

    async def get_by_hash_id(self, hash_id: str) -> Optional[UploadDTO]:
        """Get upload by hash_id (unique identifier)."""
        stmt = select(self._model).filter(self._model.hash_id == hash_id)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_dto(orm_obj) if orm_obj else None

    async def update_thumbnails_ready(
        self, id: int, ready: bool, hashes: dict | None = None
    ) -> Optional[UploadDTO]:
        """Update thumbnail generation status and hashes."""
        data = {"thumbnails_ready": ready}
        if hashes:
            if "sm" in hashes:
                data["thumbnail_sha256_sm"] = hashes["sm"]
            if "md" in hashes:
                data["thumbnail_sha256_md"] = hashes["md"]
            if "lg" in hashes:
                data["thumbnail_sha256_lg"] = hashes["lg"]
        
        return await self.update(id, data)
