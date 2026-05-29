import pytest
from httpx import AsyncClient, ASGITransport
from app_backend.main import app
from app_backend.models.user import User, UserRole

@pytest.mark.asyncio
async def test_admin_creation_permissions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Assuming app is initialized with test db
        # 1. Login as main admin
        response = await ac.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert response.status_code == 200
        main_token = response.json()["access_token"]
        
        # 2. Main admin creates sub-admin
        res = await ac.post("/api/admin/users", json={"role": "admin"}, headers={"Authorization": f"Bearer {main_token}"})
        assert res.status_code == 201
        sub_admin = res.json()["username"]
        sub_admin_pw = res.json()["generated_password"]
        
        # 3. Main admin creates mod
        res = await ac.post("/api/admin/users", json={"role": "moderator"}, headers={"Authorization": f"Bearer {main_token}"})
        assert res.status_code == 201
        
        # 4. Login as sub-admin
        res = await ac.post("/auth/login", json={"username": sub_admin, "password": sub_admin_pw})
        assert res.status_code == 200
        sub_admin_token = res.json()["access_token"]
        
        # 5. Sub admin cannot create admin
        res = await ac.post("/api/admin/users", json={"role": "admin"}, headers={"Authorization": f"Bearer {sub_admin_token}"})
        assert res.status_code == 403
        
        # 6. Sub admin can create mod
        res = await ac.post("/api/admin/users", json={"role": "moderator"}, headers={"Authorization": f"Bearer {sub_admin_token}"})
        assert res.status_code == 201
