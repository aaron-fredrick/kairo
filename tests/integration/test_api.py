def test_guest_login(client):
    """Auth join returns a token and generated username."""
    response = client.post("/auth/join", json={})
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert "username" in json_data
