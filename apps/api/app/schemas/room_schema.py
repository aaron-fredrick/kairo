from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RoomBaseSchema(BaseModel):
    name: str
    description: Optional[str] = None

class RoomCreateSchema(RoomBaseSchema):
    pass

class RoomResponseSchema(RoomBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
