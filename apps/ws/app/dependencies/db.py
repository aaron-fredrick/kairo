from app.api.dependencies.db import get_db_session
from fastapi import Depends


# Re-export from API dependencies
# WebSocket can use the same database session dependency
async def get_db_session_ws():
    """WebSocket dependency for database session."""
    async for session in get_db_session():
        yield session
