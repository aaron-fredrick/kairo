import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Verify that root endpoint is accessible (serves the static index placeholder)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Kairo" in response.text

def test_guest_login_placeholder():
    """Test guest login endpoint returns a token response placeholder."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert "username" in json_data
