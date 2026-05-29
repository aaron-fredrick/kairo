import pytest
from httpx import ASGITransport, AsyncClient

from app_backend.main import app


@pytest.mark.asyncio
async def test_dm_permissions_flow():
    """Full user workflow: admin setup, joins, DMs, and permission boundaries."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert res.status_code == 200, "Main admin login failed"
        main_token = res.json()["access_token"]

        res = await ac.post(
            "/api/admin/users",
            json={"role": "moderator"},
            headers={"Authorization": f"Bearer {main_token}"},
        )
        assert res.status_code == 201, "Admin failed to create mod"
        mod_user = res.json()["username"]

        res = await ac.post("/auth/join", json={})
        assert res.status_code == 200
        token_1 = res.json()["access_token"]

        res = await ac.post("/auth/join", json={})
        assert res.status_code == 200
        normal_2 = res.json()["username"]

        res = await ac.post(
            f"/api/dm/{normal_2}",
            json={"content": "hello"},
            headers={"Authorization": f"Bearer {token_1}"},
        )
        assert res.status_code == 200, "Normal user failed to DM another normal user"

        res = await ac.post(
            f"/api/dm/{mod_user}",
            json={"content": "hello mod"},
            headers={"Authorization": f"Bearer {token_1}"},
        )
        assert res.status_code == 200, "Normal user failed to DM moderator"

        res = await ac.post(
            "/api/dm/admin",
            json={"content": "hello admin"},
            headers={"Authorization": f"Bearer {token_1}"},
        )
        assert res.status_code == 403, "Normal user should not DM admin"
