from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.db.orm.message_orm import MessageORM
    from app.infrastructure.db.orm.upload_orm import UploadORM


class AttachmentORM(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[int] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False
    )
    # The filename as provided by the user at attachment time
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    message: Mapped["MessageORM"] = relationship(back_populates="attachments")
    upload: Mapped["UploadORM"] = relationship()
