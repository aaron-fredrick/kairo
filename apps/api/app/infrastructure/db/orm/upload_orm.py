from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin


class UploadORM(Base, TimestampMixin):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    hash_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    thumbnails_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    thumbnail_sha256_sm: Mapped[str] = mapped_column(String(64), nullable=True)
    thumbnail_sha256_md: Mapped[str] = mapped_column(String(64), nullable=True)
    thumbnail_sha256_lg: Mapped[str] = mapped_column(String(64), nullable=True)
