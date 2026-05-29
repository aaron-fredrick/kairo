def test_websocket_connection(client):
    """Client can connect to a room WebSocket and send a message."""
    res = client.post("/auth/join", json={})
    assert res.status_code == 200
    token = res.json()["access_token"]

    with client.websocket_connect(f"/ws/chat/1?token={token}") as websocket:
        websocket.send_json({"event": "message", "content": "test message"})

        data = None
        for _ in range(8):
            data = websocket.receive_json()
            if data.get("event") == "new_message":
                break
        assert data is not None
        assert data["event"] == "new_message"
        assert data["content"] == "test message"
