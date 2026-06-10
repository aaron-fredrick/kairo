from sqlalchemy import Column, BigInteger, ForeignKey, String, Boolean, Integer, text
from database.models.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    message_id = Column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )

    filename = Column(String)
    mime_type = Column(String)
    size_bytes = Column(Integer)

    blob_ready = Column(Boolean, default=False)
    thumbnails_ready = Column(Boolean, default=False)

    storage_backend = Column(String)
    storage_path = Column(String)
    bucket = Column(String)
    sha256 = Column(String)
    storage_key = Column(String)

    thumbnail_128_key = Column(String)
    thumbnail_512_key = Column(String)
    thumbnail_1024_key = Column(String)