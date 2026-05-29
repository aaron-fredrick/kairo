"""HTTP API flows via TestClient."""
import io

import pytest
from PIL import Image


@pytest.fixture
def auth_headers(client):
    res = client.post("/auth/join", json={})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_invalid_credentials(client):
    res = client.post("/auth/login", json={"username": "nobody", "password": "wrong"})
    assert res.status_code == 401


def test_users_me(client, auth_headers):
    res = client.get("/api/users/me", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "username" in body
    assert body["role"] == "normal"


def test_list_rooms(client, auth_headers):
    res = client.get("/api/rooms", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


def test_room_messages_and_presence(client, auth_headers):
    res = client.get("/api/rooms/1/messages", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    pres = client.get("/api/rooms/1/presence", headers=auth_headers)
    assert pres.status_code == 200
    assert "users" in pres.json()


def test_presence_global(client, auth_headers):
    res = client.get("/api/users/presence/1", headers=auth_headers)
    assert res.status_code == 200
    assert "online_usernames" in res.json()


def test_upload_file_staging(client, auth_headers):
    img = Image.new("RGB", (8, 8), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    res = client.post(
        "/api/data/upload/file",
        headers=auth_headers,
        files={"file": ("pixel.png", buf, "image/png")},
        data={"room_id": "1"},
    )
    assert res.status_code == 201
    body = res.json()
    assert "upload_id" in body
    assert body["mime_type"].startswith("image/")


def test_upload_pfp_staging(client, auth_headers):
    img = Image.new("RGB", (16, 16), color=(255, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    res = client.post(
        "/api/data/upload/pfp",
        headers=auth_headers,
        files={"file": ("face.png", buf, "image/png")},
    )
    assert res.status_code == 200
    assert "pfp_upload_id" in res.json()


def test_openapi_and_docs(client):
    assert client.get("/openapi.json").status_code == 200
