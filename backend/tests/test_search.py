from app.db import seed_default_user
from app.security import hash_password
from app.tables import Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def _make_session(client, db, title: str, content: str) -> dict:
    session = client.post("/api/sessions").json()
    session_id = session["id"]
    client.patch(f"/api/sessions/{session_id}", json={"title": title})
    msg = Message(
        session_id=session_id,
        role="user",
        content=content,
        model_name="Test",
        model="test-model",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": session_id, "message_id": msg.id}


def test_search_and_tokens_title_or_content(client, db, settings):
    _login(client, db, settings)

    s1 = _make_session(client, db, "社会学笔记", "韦伯")
    s2 = _make_session(client, db, "闲聊", "韦伯 人类学")

    r = client.get("/api/search", params={"q": "韦伯 人类学"})
    assert r.status_code == 200
    body = r.json()
    assert "sessions" in body
    ids = [s["id"] for s in body["sessions"]]
    assert ids == [s2["id"]]
    assert body["sessions"][0]["hit_message_id"] == s2["message_id"]
    assert "韦伯" in body["sessions"][0]["snippet"] or "人类学" in body["sessions"][0]["snippet"]

    r2 = client.get("/api/search", params={"q": "社会学"})
    assert r2.status_code == 200
    hits = r2.json()["sessions"]
    assert [s["id"] for s in hits] == [s1["id"]]
    assert hits[0]["hit_message_id"] is None
    assert "社会学" in hits[0]["snippet"]

    assert client.delete(f"/api/sessions/{s1['id']}").status_code == 200
    hidden = client.get("/api/search", params={"q": "社会学"}).json()["sessions"]
    assert all(s["id"] != s1["id"] for s in hidden)


def test_search_requires_auth(client, db, settings):
    r = client.get("/api/search", params={"q": "韦伯"})
    assert r.status_code in (401, 403)
