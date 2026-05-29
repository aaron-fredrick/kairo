from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_available():
    """API process is up and serving (no frontend build required)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Kairo API"


def test_guest_join_responds():
    """Critical auth endpoint is reachable."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    assert "access_token" in response.json()
