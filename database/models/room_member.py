from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, PrimaryKeyConstraint, text
from database.models.base import Base


class RoomMember(Base):
    __tablename__ = "room_members"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(BigInteger, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)

    joined_at = Column(DateTime, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "room_id", name="membership"),
    )