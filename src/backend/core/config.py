import os
import logging
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


env = os.getenv("ENV", "development").lower()

if env != "production":
    load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env" if env != "production" else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVER_PASSWORD: Optional[str] = os.getenv("SERVER_PASSWORD")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
    USER_LIMIT: Optional[int] = int(os.getenv("USER_LIMIT")) if os.getenv("USER_LIMIT") else None
    IP_BLACKLIST: str = os.getenv("IP_BLACKLIST", "")
    IP_WHITELIST: str = os.getenv("IP_WHITELIST", "")
    ADJECTIVES_FILE: str = os.getenv("ADJECTIVES_FILE", "config/adjectives.txt")
    NOUNS_FILE: str = os.getenv("NOUNS_FILE", "config/nouns.txt")

    ENV: str = env
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes", "y")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    EVENT_BUS: str = os.getenv("EVENT_BUS", "local")
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173"
    )

    DB_BACKEND: str = os.getenv("DB_BACKEND", "postgres")
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./data/db/kairo.db")

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "kairo")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "kairo_password")
    DB_NAME: str = os.getenv("DB_NAME", "kairo")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{os.getenv('DB_USER', 'kairo')}:{os.getenv('DB_PASSWORD', 'kairo_password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kairo')}"
    )

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
    )

    UPLOAD_BACKEND: str = os.getenv("UPLOAD_BACKEND", "local")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    UPLOAD_MAX_SIZE_MB: int = int(os.getenv("UPLOAD_MAX_SIZE_MB", "50"))
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000/api")

    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")

    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:7000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "username")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "password")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "kairo")
    MINIO_REGION: str = os.getenv("MINIO_REGION", "us-east-1")

    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        "super_secret_jwt_key_change_me_in_production_1234567890"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
    )

    REGISTER_ENABLED: bool = os.getenv("REGISTER_ENABLED", "false").lower() in (
        "true", "1", "t", "yes", "y"
    )
    REGISTER_URL: str = os.getenv("REGISTER_URL", "")
    REGISTER_SYSTEM_KEY: str = os.getenv("REGISTER_SYSTEM_KEY", "")
    REGISTER_INSTANCE_HOST: str = os.getenv("REGISTER_INSTANCE_HOST", "127.0.0.1")
    REGISTER_INSTANCE_PORT: int = int(os.getenv("REGISTER_INSTANCE_PORT", str(PORT)))
    REGISTER_INSTANCE_SCHEME: str = os.getenv("REGISTER_INSTANCE_SCHEME", "http")
    REGISTER_INSTANCE_NAME: str = os.getenv("REGISTER_INSTANCE_NAME", "")
    REGISTER_HEARTBEAT_INTERVAL: int = int(
        os.getenv("REGISTER_HEARTBEAT_INTERVAL", "15")
    )

    @property
    def blacklist_ips(self) -> list[str]:
        return [ip.strip() for ip in self.IP_BLACKLIST.split(",")] if self.IP_BLACKLIST else []

    @property
    def whitelist_ips(self) -> list[str]:
        return [ip.strip() for ip in self.IP_WHITELIST.split(",")] if self.IP_WHITELIST else []

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def USE_REDIS(self) -> bool:
        return self.EVENT_BUS == "redis"

    @property
    def TEMP_UPLOAD_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "temp", "uploads")

    @property
    def BLOB_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "blobs")

    @property
    def THUMBNAIL_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "thumbnails")

    @property
    def is_object_storage(self) -> bool:
        return self.UPLOAD_BACKEND.lower() in ("s3", "minio")

    def object_storage_config(self, backend: Optional[str] = None) -> dict[str, str]:
        name = (backend or self.UPLOAD_BACKEND).lower()

        if name == "minio":
            return {
                "bucket": self.MINIO_BUCKET,
                "region": self.MINIO_REGION,
                "access_key": self.MINIO_ACCESS_KEY,
                "secret_key": self.MINIO_SECRET_KEY,
                "endpoint_url": self.MINIO_ENDPOINT,
            }

        if name == "s3":
            return {
                "bucket": self.S3_BUCKET,
                "region": self.S3_REGION,
                "access_key": self.S3_ACCESS_KEY,
                "secret_key": self.S3_SECRET_KEY,
                "endpoint_url": self.S3_ENDPOINT_URL or "",
            }

        raise ValueError(f"Invalid object storage backend: {name}")

    def validate_environment(self):
        warnings = []
        errors = []

        weak_passwords = {"admin", "password", "123456", "changeme"}

        if self.ENV == "production":
            if self.ADMIN_PASSWORD.lower() in weak_passwords or len(self.ADMIN_PASSWORD) < 12:
                warnings.append("Weak ADMIN_PASSWORD")

            if self.DB_PASSWORD.lower() in weak_passwords or len(self.DB_PASSWORD) < 12:
                warnings.append("Weak DB_PASSWORD")

            if self.DB_BACKEND != "postgres":
                warnings.append("DB_BACKEND forced to postgres in production")

            if "sqlite" in self.DATABASE_URL.lower():
                errors.append("DATABASE_URL cannot use sqlite in production")

            if self.EVENT_BUS != "redis":
                warnings.append("EVENT_BUS forced to redis in production")

            if "*" in self.cors_origins_list:
                errors.append("CORS wildcard not allowed in production")

            if self.UPLOAD_BACKEND not in ("s3", "minio"):
                errors.append("UPLOAD_BACKEND must be s3 or minio in production")

            if not self.REGISTER_URL:
                errors.append("REGISTER_URL required in production")

        for warning in warnings:
            logger.warning(warning)

        if errors:
            for error in errors:
                logger.error(error)
            raise RuntimeError("Production configuration validation failed")

        if self.ENV == "production":
            self.DB_BACKEND = "postgres"
            self.EVENT_BUS = "redis"


settings = Settings()
settings.validate_environment()