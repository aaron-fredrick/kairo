from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MessageDTO:
    id: int
    content: str
    sender_id: int
    room_id: int
    created_at: datetime
    updated_at: datetime
    attachment_ids: list[int] = field(default_factory=list)
