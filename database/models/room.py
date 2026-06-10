from sqlalchemy import Column, BigInteger, String, text
from database.models.base import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    created_at = Column(nullable=False, server_default=text("now()"))
    updated_at = Column(nullable=False, server_default=text("now()"))