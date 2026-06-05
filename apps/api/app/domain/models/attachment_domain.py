from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class AttachmentDomain:
    id: int
    message_id: int
    upload_id: int
    filename: str
    created_at: datetime
    updated_at: datetime
