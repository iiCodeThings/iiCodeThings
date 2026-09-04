from app.db import seed_default_user
from app.security import hash_password
from app.tables import ChatSession


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_sessions_crud(client, db, settings):
    _login(client, db, settings)

    r = client.post("/api/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "新对话"
    session_id = body["id"]

    r = client.patch(f"/api/sessions/{session_id}", json={"title": "重命名会话"})
    assert r.status_code == 200
    assert r.json()["title"] == "重命名会话"

    r = client.delete(f"/api/sessions/{session_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    listed = client.get("/api/sessions").json()
    assert all(s["id"] != session_id for s in listed)

    db.expire_all()
    row = db.get(ChatSession, session_id)
    assert row is not None
    assert row.deleted_at is not None

    r = client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 404
    r = client.patch(f"/api/sessions/{session_id}", json={"title": "不应改名"})
    assert r.status_code == 404
    r = client.delete(f"/api/sessions/{session_id}")
    assert r.status_code == 404
