from sqlalchemy import Column, BigInteger, ForeignKey, Boolean, String, text
from database.models.base import Base


class Pfp(Base):
    __tablename__ = "pfps"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    blob_ready = Column(Boolean, default=False)
    thumbnails_ready = Column(Boolean, default=False)

    storage_backend = Column(String)
    storage_path = Column(String)
    bucket = Column(String)
    sha256 = Column(String)

    thumb_128_key = Column(String)
    thumb_512_key = Column(String)
    thumb_1024_key = Column(String)

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"))