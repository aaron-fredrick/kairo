"""Auth service join and capacity."""
import pytest
from httpx import AsyncClient, ASGITransport

from app_backend.core.state import get_state_manager
from app_backend.db.database import AsyncSessionLocal
from app_backend.main import app
from app_backend.services.auth_service import auth_service


@pytest.mark.asyncio
async def test_join_server_assigns_username():
    async with AsyncSessionLocal() as db:
        state = await get_state_manager()
        username, token = await auth_service.join_server(state, db, password=None)
        assert username
        assert token
        assert await state.is_user_active(username)


@pytest.mark.asyncio
async def test_join_via_http():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/auth/join", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "normal"
