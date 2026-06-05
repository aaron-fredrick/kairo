from dataclasses import dataclass, field
from datetime import datetime

from app.domain.models.attachment_domain import AttachmentDomain


@dataclass
class MessageDomain:
    id: int
    content: str
    sender_id: int
    room_id: int
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentDomain] = field(default_factory=list)
