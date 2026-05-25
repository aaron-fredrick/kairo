from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import TimestampMixin


class Upload(Base, TimestampMixin):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Human-readable identity
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Storage
    hash_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False)  # local | s3 | ftp
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)           # backend-relative path

    # Integrity hashes
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Thumbnail state — stored as a simple flag; actual URLs are derived
    thumbnails_ready: Mapped[bool] = mapped_column(default=False, nullable=False)
    thumbnail_sha256_sm: Mapped[str] = mapped_column(String(64), nullable=True)
    thumbnail_sha256_md: Mapped[str] = mapped_column(String(64), nullable=True)
    thumbnail_sha256_lg: Mapped[str] = mapped_column(String(64), nullable=True)
