from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from src.backend.db.database import Base
from src.backend.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.backend.models.user import User
    from src.backend.models.room import Room
    from src.backend.models.attachment import Attachment

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    sender: Mapped["User"] = relationship(back_populates="messages")
    room: Mapped["Room"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="message", cascade="all, delete-orphan", lazy="selectin")
