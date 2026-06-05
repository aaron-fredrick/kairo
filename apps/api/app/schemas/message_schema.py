from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageBaseSchema(BaseModel):
    content: str
    room_id: int

class MessageCreateSchema(MessageBaseSchema):
    pass

class MessageResponseSchema(MessageBaseSchema):
    id: int
    sender_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AttachmentInfoSchema(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int
    url: Optional[str] = None

class MessageWithAttachmentsResponseSchema(MessageResponseSchema):
    attachments: List[AttachmentInfoSchema] = []