"""Direct message API."""
def test_normal_users_can_dm_each_other(client):
    a = client.post("/auth/join", json={}).json()
    b = client.post("/auth/join", json={}).json()
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    res = client.post(
        f"/api/dm/{b['username']}",
        headers=headers,
        json={"content": "hello"},
    )
    assert res.status_code == 200
    assert res.json()["content"] == "hello"


def test_dm_history(client):
    a = client.post("/auth/join", json={}).json()
    b = client.post("/auth/join", json={}).json()
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    client.post(f"/api/dm/{b['username']}", headers=headers, json={"content": "ping"})
    hist = client.get(f"/api/dm/{b['username']}", headers=headers)
    assert hist.status_code == 200
    assert len(hist.json()) >= 1
