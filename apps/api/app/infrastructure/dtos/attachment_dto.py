from dataclasses import dataclass
from datetime import datetime


@dataclass
class AttachmentDTO:
    id: int
    message_id: int
    upload_id: int
    filename: str
    created_at: datetime
    updated_at: datetime
