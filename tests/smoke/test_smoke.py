import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_smoke_end_to_end():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login as main admin
        res = await ac.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert res.status_code == 200, "Main admin login failed"
        main_token = res.json()["access_token"]
        
        # 2. Admin creates a mod
        res = await ac.post("/api/admin/users", json={"role": "moderator"}, headers={"Authorization": f"Bearer {main_token}"})
        assert res.status_code == 201, "Admin failed to create mod"
        mod_user = res.json()["username"]
        
        # 3. Join two normal users
        res = await ac.post("/auth/join", json={})
        assert res.status_code == 200
        normal_1 = res.json()["username"]
        token_1 = res.json()["access_token"]
        
        res = await ac.post("/auth/join", json={})
        assert res.status_code == 200
        normal_2 = res.json()["username"]
        token_2 = res.json()["access_token"]
        
        # 4. Normal 1 DMs Normal 2
        res = await ac.post(f"/api/dm/{normal_2}", json={"content": "hello"}, headers={"Authorization": f"Bearer {token_1}"})
        assert res.status_code == 200, "Normal 1 failed to DM Normal 2"
        
        # 5. Normal 1 DMs Mod
        res = await ac.post(f"/api/dm/{mod_user}", json={"content": "hello mod"}, headers={"Authorization": f"Bearer {token_1}"})
        assert res.status_code == 200, "Normal 1 failed to DM Mod"
        
        # 6. Normal 1 fails to DM Admin
        res = await ac.post(f"/api/dm/admin", json={"content": "hello admin"}, headers={"Authorization": f"Bearer {token_1}"})
        assert res.status_code == 403, "Normal 1 should not be able to DM admin"
