from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_guest_login():
    """Auth join returns a token and generated username."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert "username" in json_data
