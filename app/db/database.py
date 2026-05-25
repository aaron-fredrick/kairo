from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Select DB URL and engine arguments based on settings
db_url = settings.SQLITE_URL if settings.USE_SQLITE else settings.DATABASE_URL
engine_kwargs = {"echo": settings.DEBUG, "future": True}

if settings.USE_SQLITE:
    # SQLite-specific arguments
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Postgres-specific arguments
    engine_kwargs["pool_pre_ping"] = True

# Create asynchronous engine
engine = create_async_engine(db_url, **engine_kwargs)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Dependency to inject async DB session into FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
