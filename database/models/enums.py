import enum


class AuthType(str, enum.Enum):
    anonymous = "anonymous"
    password = "password"
    oauth = "oauth"


class UserType(str, enum.Enum):
    admin = "admin"
    anonymous = "anonymous"