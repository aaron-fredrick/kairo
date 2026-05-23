import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_connection():
    """Verify that a client can successfully connect to the WebSocket channel endpoint."""
    with client.websocket_connect("/ws/chat/1") as websocket:
        # Send a hello/echo event
        websocket.send_json({"event": "message", "content": "test message"})
        
        # Verify socket broadcasts/echoes it back
        data = websocket.receive_json()
        assert data["event"] == "message"
        assert data["content"] == "test message"
