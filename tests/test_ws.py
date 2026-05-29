import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_connection():
    """Verify that a client can successfully connect to the WebSocket channel endpoint."""
    # Authenticate to get a token
    res = client.post("/auth/join", json={})
    assert res.status_code == 200
    token = res.json()["access_token"]

    with client.websocket_connect(f"/ws/chat/1?token={token}") as websocket:
        # Send a hello/echo event
        websocket.send_json({"event": "message", "content": "test message"})
        
        # Verify socket broadcasts/echoes it back (may receive presence update first)
        data = websocket.receive_json()
        if data.get("event") == "presence_update":
            data = websocket.receive_json()
            
        assert data["event"] == "new_message"
        assert data["content"] == "test message"
