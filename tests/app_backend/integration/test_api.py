def test_guest_login(client):
    """Auth join returns a token and generated username."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert "username" in json_data


def test_admin_login(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_dm_permission_denied_for_guest_to_admin(client):
    """Normal user cannot open DM to admin via API."""
    guest = client.post("/auth/join", json={}).json()
    headers = {"Authorization": f"Bearer {guest['access_token']}"}
    admin_login = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()
    res = client.post(
        f"/api/dm/{admin_login['username']}",
        headers=headers,
        json={"content": "hi"},
    )
    assert res.status_code == 403
