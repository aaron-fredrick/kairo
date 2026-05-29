from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_websocket_connection():
    """Client can connect to a room WebSocket and send a message."""
    res = client.post("/auth/join", json={})
    assert res.status_code == 200
    token = res.json()["access_token"]

    with client.websocket_connect(f"/ws/chat/1?token={token}") as websocket:
        websocket.send_json({"event": "message", "content": "test message"})

        data = websocket.receive_json()
        if data.get("event") == "presence_update":
            data = websocket.receive_json()

        assert data["event"] == "new_message"
        assert data["content"] == "test message"
