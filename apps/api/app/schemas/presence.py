from pydantic import BaseModel
from typing import List

class PresenceUpdateResponse(BaseModel):
    status: str
    last_seen: int

class OnlineUsersResponse(BaseModel):
    online_users: List[int]
