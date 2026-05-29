from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root():
    """App serves the frontend shell at /."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Kairo" in response.text


def test_guest_join_responds():
    """Critical auth endpoint is reachable."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    assert "access_token" in response.json()
