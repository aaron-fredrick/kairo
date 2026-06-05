from dataclasses import dataclass
from datetime import datetime


@dataclass
class RoomDTO:
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
