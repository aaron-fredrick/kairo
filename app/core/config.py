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
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
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
    HOST: str = os.getenv("HOST", "127.0.0.1")
    EVENT_BUS: str = os.getenv("EVENT_BUS", "local")  # "local" | "redis"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Database Settings
    DB_BACKEND: str = os.getenv("DB_BACKEND", "postgres")  # "sqlite" | "postgres"
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./data/db/kairo.db")

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "kairo")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "kairo_password")
    DB_NAME: str = os.getenv("DB_NAME", "kairo")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{os.getenv('DB_USER', 'kairo')}:{os.getenv('DB_PASSWORD', 'kairo_password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kairo')}")

    # Redis Settings
    @property
    def USE_REDIS(self) -> bool:
        return self.EVENT_BUS == "redis"

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0")

    # Storage paths — everything lives under DATA_DIR
    UPLOAD_BACKEND: str = os.getenv("UPLOAD_BACKEND", "local")   # local | s3 | ftp
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    UPLOAD_MAX_SIZE_MB: int = int(os.getenv("UPLOAD_MAX_SIZE_MB", "50"))
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

    @property
    def TEMP_UPLOAD_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "temp", "uploads")

    @property
    def BLOB_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "blobs")

    @property
    def THUMBNAIL_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "thumbnails")

    # S3 Storage (when UPLOAD_BACKEND=s3)
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")  # for MinIO etc.

    # FTP Storage (when UPLOAD_BACKEND=ftp)
    FTP_HOST: str = os.getenv("FTP_HOST", "localhost")
    FTP_PORT: int = int(os.getenv("FTP_PORT", "21"))
    FTP_USER: str = os.getenv("FTP_USER", "")
    FTP_PASSWORD: str = os.getenv("FTP_PASSWORD", "")
    FTP_REMOTE_DIR: str = os.getenv("FTP_REMOTE_DIR", "/uploads")

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key_change_me_in_production_1234567890")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5"))

settings = Settings()
