import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # Auth and Access Control
    SERVER_PASSWORD: Optional[str] = os.getenv("SERVER_PASSWORD")
    USER_LIMIT: Optional[int] = int(os.getenv("USER_LIMIT")) if os.getenv("USER_LIMIT") else None
    IP_BLACKLIST: str = os.getenv("IP_BLACKLIST", "")
    IP_WHITELIST: str = os.getenv("IP_WHITELIST", "")
    ADJECTIVES_FILE: str = os.getenv("ADJECTIVES_FILE", "config/adjectives.txt")
    NOUNS_FILE: str = os.getenv("NOUNS_FILE", "config/nouns.txt")

    @property
    def blacklist_ips(self) -> list[str]:
        return [ip.strip() for ip in self.IP_BLACKLIST.split(",")] if self.IP_BLACKLIST else []
        
    @property
    def whitelist_ips(self) -> list[str]:
        return [ip.strip() for ip in self.IP_WHITELIST.split(",")] if self.IP_WHITELIST else []

    # General Settings
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes", "y")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # PostgreSQL Database Settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "kairo")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "kairo_password")
    DB_NAME: str = os.getenv("DB_NAME", "kairo")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{os.getenv('DB_USER', 'kairo')}:{os.getenv('DB_PASSWORD', 'kairo_password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kairo')}")

    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0")

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key_change_me_in_production_1234567890")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

settings = Settings()
