import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = os.getenv("ENV", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes", "y")

    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173"
    )

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "kairo_api_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "kairo_api_pass")
    DB_NAME: str = os.getenv("DB_NAME", "kairo")
    
    @property
    def DATABASE_URL(self) -> str:
        if self.ENV == "production" or os.getenv("DB_BACKEND", "postgres") == "postgres":
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./data/db/kairo.db")
    
    # Redis
    REDIS_URL: str | None = os.getenv("REDIS_HOST", None)
    

    # Storage
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local") # s3, minio, local
    S3_BUCKET: str = os.getenv("S3_BUCKET", "kairo")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key_change_me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5"))

    # Config files for random name gen
    ADJECTIVES_FILE: str = os.getenv("ADJECTIVES_FILE", "config/adjectives.txt")
    NOUNS_FILE: str = os.getenv("NOUNS_FILE", "config/nouns.txt")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        
    def validate_production(self):
        if self.ENV == "production":
            self.STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "s3") # force s3 or minio in prod logic check
            if self.STORAGE_BACKEND not in ("s3", "minio"):
                raise ValueError("STORAGE_BACKEND must be s3 or minio in production")
            if not self.S3_ACCESS_KEY or not self.S3_SECRET_KEY:
                raise ValueError("Storage credentials missing for production")

settings = Settings()
try:
    settings.validate_production()
except ValueError as e:
    logger.error("Configuration error", error=str(e))
    exit(1)
