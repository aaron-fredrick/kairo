"""Register HTTP API component tests."""
from __future__ import annotations

import json

from shared.service_auth import sign_headers

SYSTEM_KEY = "test-register-system-key"


def _system_headers(method: str, path: str, body: bytes = b"") -> dict[str, str]:
    headers = sign_headers(SYSTEM_KEY, method, path, body)
    if body:
        headers["Content-Type"] = "application/json"
    return headers


def test_health_unauthenticated(register_client) -> None:
    resp = register_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_list_deregister_flow(register_client) -> None:
    body = json.dumps({"host": "app", "port": 8000, "hostname": "node-a"}).encode()
    path = "/api/v1/register"
    reg = register_client.post(path, content=body, headers=_system_headers("POST", path, body))
    assert reg.status_code == 200
    data = reg.json()
    server_id = data["server_id"]
    heartbeat_secret = data["heartbeat_secret"]

    list_path = "/api/v1/servers"
    listed = register_client.get(list_path, headers=_system_headers("GET", list_path))
    assert listed.status_code == 200
    assert len(listed.json()["healthy"]) == 1

    hb_path = f"/api/v1/heartbeat/{server_id}"
    hb = register_client.post(
        hb_path,
        content=b"",
        headers=sign_headers(heartbeat_secret, "POST", hb_path, b""),
    )
    assert hb.status_code == 200

    del_path = f"/api/v1/register/{server_id}"
    deleted = register_client.delete(del_path, headers=_system_headers("DELETE", del_path))
    assert deleted.status_code == 204

    listed_after = register_client.get(list_path, headers=_system_headers("GET", list_path))
    assert listed_after.json()["healthy"] == []


def test_register_rejects_bad_hmac(register_client) -> None:
    body = b'{"host":"app","port":8000}'
    path = "/api/v1/register"
    headers = sign_headers("wrong-key", "POST", path, body)
    headers["Content-Type"] = "application/json"
    resp = register_client.post(path, content=body, headers=headers)
    assert resp.status_code == 401
