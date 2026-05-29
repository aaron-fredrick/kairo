"""File upload over WebSocket confirm flow."""
import io

from PIL import Image


def test_file_upload_confirm_via_websocket(client):
    join = client.post("/auth/join", json={}).json()
    token = join["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    img = Image.new("RGB", (12, 12), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    staged = client.post(
        "/api/data/upload/file",
        headers=headers,
        files={"file": ("chart.png", buf, "image/png")},
        data={"room_id": "1"},
    )
    assert staged.status_code == 201
    meta = staged.json()

    with client.websocket_connect(f"/ws/chat/1?token={token}") as ws:
        ws.send_json({
            "event": "message",
            "content": "",
            "attachments": [{
                "upload_id": meta["upload_id"],
                "filename": meta["original_filename"],
                "mime_type": meta["mime_type"],
                "size_bytes": meta["size_bytes"],
            }],
        })
        data = ws.receive_json()
        while data.get("event") == "presence_update":
            data = ws.receive_json()
        assert data["event"] == "new_message"
        assert data.get("attachments")
