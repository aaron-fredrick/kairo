from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.message import Message

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=True) # Nullable for anonymous guests
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    messages: Mapped[List["Message"]] = relationship(back_populates="sender", cascade="all, delete-orphan")
