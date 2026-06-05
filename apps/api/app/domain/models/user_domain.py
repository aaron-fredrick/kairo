from dataclasses import dataclass


@dataclass
class UserDomain:
    id: int
    username: str
    pfp_hash: str | None
    is_anonymous: bool
    is_superadmin: bool
    role: str
