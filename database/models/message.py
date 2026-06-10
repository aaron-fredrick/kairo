from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, text
from database.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    room_id = Column(
        BigInteger,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"))