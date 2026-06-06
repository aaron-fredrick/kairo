import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger(__name__)

from pathlib import Path
import os


class ConfigResolver:
    def __init__(self, environment: str):
        self.environment = environment

    def read_secret(self, name: str) -> str | None:
        path = Path(f"/run/secrets/{name}")
        if path.exists():
            value = path.read_text().strip()
            return value or None
        return None

    def resolve(
        self,
        env_name: str,
        secret_name: str | None = None,
        default: str | None = None,
        required_in_production: bool = True,
    ) -> str:

        secret_name = secret_name or env_name.lower()

        secret_value = self.read_secret(secret_name)
        env_value = os.getenv(env_name)

        # 1. Production: secrets ONLY
        if self.environment == "production":
            if secret_value:
                return secret_value

            if required_in_production:
                raise RuntimeError(
                    f"Missing required secret: {secret_name}"
                )

            return env_value or default

        # 2. Non-production: secret → env → default
        if secret_value:
            return secret_value

        if env_value:
            return env_value

        if self.environment == "development":
            return default or f"DEV_{env_name}_DEFAULT"

        # staging/test fallback
        return default or env_value or ""

from functools import cached_property

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
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173"
    )

    # Observability
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "False").lower() in ("true", "1", "t", "yes", "y")

    # Database
    DATABASE_URL: str | None = None
    
    # Redis
    REDIS_URL: str | None = os.getenv("REDIS_HOST", None)
    

    # Storage
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local") # s3, minio, local
    S3_BUCKET: str = os.getenv("S3_BUCKET", "kairo")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")

    # Auth
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5"))
    REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "30"))

    # Config files for random name gen
    ADJECTIVES_FILE: str = os.getenv("ADJECTIVES_FILE", "config/adjectives.txt")
    NOUNS_FILE: str = os.getenv("NOUNS_FILE", "config/nouns.txt")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @cached_property
    def resolver(self):
        return ConfigResolver(self.ENV)

    def load(self):
        r = self.resolver

        self.JWT_SECRET = r.resolve(
            env_name="JWT_SECRET",
            secret_name="jwt_secret",
            default="super_secret_jwt_key_change_me",
            required_in_production=True,
        )

        db_backend = os.getenv("DB_BACKEND", "sqlite" if self.ENV == "development" else "postgres")
        if db_backend == "postgres":
            db_user = r.resolve("DB_USER", default="kairo_api_user", required_in_production=True)
            db_pass = r.resolve("DB_PASSWORD", default="kairo_api_pass", required_in_production=True)
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "kairo")
            default_db_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        else:
            default_db_url = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///kairo.db")

        self.DATABASE_URL = r.resolve(
            env_name="DATABASE_URL",
            secret_name="database_url",
            default=default_db_url,
            required_in_production=True,
        )

        self.S3_ACCESS_KEY = r.resolve(
            env_name="S3_ACCESS_KEY",
            secret_name="s3_access_key",
            default="",
            required_in_production=False,
        )

        self.S3_SECRET_KEY = r.resolve(
            env_name="S3_SECRET_KEY",
            secret_name="s3_secret_key",
            default="",
            required_in_production=False,
        )

        return self
        
    def validate_production(self):
        if self.ENV == "production":
            self.STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "s3") # force s3 or minio in prod logic check
            if self.STORAGE_BACKEND not in ("s3", "minio"):
                raise ValueError("STORAGE_BACKEND must be s3 or minio in production")
            if not self.S3_ACCESS_KEY or not self.S3_SECRET_KEY:
                raise ValueError("Storage credentials missing for production")

settings = Settings().load()
try:
    settings.validate_production()
except ValueError as e:
    logger.error("Configuration error", error=str(e))
    exit(1)
