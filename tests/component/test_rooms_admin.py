"""Room management by privileged users."""


def test_admin_creates_room(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    res = client.post(
        "/api/rooms",
        headers=headers,
        json={"name": "ci-test-room", "description": "temporary"},
    )
    assert res.status_code == 201
    assert res.json()["name"] == "ci-test-room"


def test_duplicate_room_name_rejected(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    client.post("/api/rooms", headers=headers, json={"name": "dup-room"})
    res = client.post("/api/rooms", headers=headers, json={"name": "dup-room"})
    assert res.status_code == 400
