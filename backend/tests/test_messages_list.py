from app.db import seed_default_user
from app.security import hash_password
from app.tables import Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_list_messages_pagination(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]

    for i in range(3):
        db.add(
            Message(
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"msg-{i}",
                model_name="Test",
                model="test-model",
            )
        )
    db.commit()

    r = client.get(f"/api/sessions/{session_id}/messages", params={"limit": 2})
    assert r.status_code == 200
    body = r.json()
    assert "messages" in body
    msgs = body["messages"]
    assert len(msgs) == 2
    ids = [m["id"] for m in msgs]
    assert ids == sorted(ids)
    assert ids[0] < ids[1]

    min_id = min(ids)
    r2 = client.get(
        f"/api/sessions/{session_id}/messages",
        params={"before_id": min_id, "limit": 2},
    )
    assert r2.status_code == 200
    earlier = r2.json()["messages"]
    assert len(earlier) == 1
    assert earlier[0]["id"] < min_id
