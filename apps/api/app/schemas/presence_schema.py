from pydantic import BaseModel
from typing import List

class PresenceUpdateResponseSchema(BaseModel):
    status: str
    last_seen: int

class OnlineUsersResponseSchema(BaseModel):
    online_users: List[int]
