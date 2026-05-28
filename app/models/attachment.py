from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.upload import Upload

class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    
    # The filename as specified by the user when attached to this specific message
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    message: Mapped["Message"] = relationship(back_populates="attachments")
    upload: Mapped["Upload"] = relationship()
