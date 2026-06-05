from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserDTO:
    id: int
    username: str
    hashed_password: str | None
    pfp_hash: str | None
    is_anonymous: bool
    is_superadmin: bool
    role: str
    created_at: datetime
    updated_at: datetime
