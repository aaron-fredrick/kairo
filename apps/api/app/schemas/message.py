from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageBase(BaseModel):
    content: str
    room_id: int

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AttachmentInfo(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int
    url: Optional[str] = None

class MessageWithAttachmentsResponse(MessageResponse):
    attachments: List[AttachmentInfo] = []