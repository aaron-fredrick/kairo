from datetime import datetime
from pydantic import BaseModel, ConfigDict


class APIBaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime