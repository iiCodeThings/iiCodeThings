from app.db import seed_default_user
from app.security import hash_password
from app.tables import ChatSession, Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def _add_turn(db, session_id, question, answer, reasoning="secret"):
    user = Message(
        session_id=session_id,
        role="user",
        content=question,
        reasoning=None,
        model_name="Display",
        model="api-id",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    asst = Message(
        session_id=session_id,
        role="assistant",
        content=answer,
        reasoning=reasoning,
        model_name="Display",
        model="api-id",
    )
    db.add(asst)
    db.commit()
    db.refresh(asst)
    return user, asst


def test_create_share_requires_login(client):
    r = client.post("/api/sessions/1/share")
    assert r.status_code == 401


def test_session_share_is_public_and_omits_reasoning(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    client.patch(f"/api/sessions/{session_id}", json={"title": "韦伯笔记"})
    _add_turn(db, session_id, "韦伯是谁？", "一位社会学家。")

    created = client.post(f"/api/sessions/{session_id}/share")
    assert created.status_code == 200
    body = created.json()
    assert body["token"]
    assert body["path"] == f"/s/{body['token']}"
    again = client.post(f"/api/sessions/{session_id}/share")
    assert again.json()["token"] == body["token"]

    client.cookies.clear()
    r = client.get(f"/api/shares/{body['token']}")
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "session"
    assert data["title"] == "韦伯笔记"
    assert [m["role"] for m in data["messages"]] == ["user", "assistant"]
    assert data["messages"][0]["content"] == "韦伯是谁？"
    assert data["messages"][1]["content"] == "一位社会学家。"
    assert "reasoning" not in data["messages"][0]
    assert "reasoning" not in data["messages"][1]


def test_turn_share_only_includes_that_pair(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    first_user, _ = _add_turn(db, session_id, "第一问", "第一答")
    second_user, _ = _add_turn(db, session_id, "第二问", "第二答")

    r = client.post(
        f"/api/sessions/{session_id}/share/turn",
        json={"user_message_id": second_user.id},
    )
    assert r.status_code == 200
    token = r.json()["token"]
    client.cookies.clear()
    data = client.get(f"/api/shares/{token}").json()
    assert data["kind"] == "turn"
    assert [m["content"] for m in data["messages"]] == ["第二问", "第二答"]
    assert first_user.content not in [m["content"] for m in data["messages"]]


def test_share_unknown_token_404(client):
    r = client.get("/api/shares/no-such-token")
    assert r.status_code == 404


def test_share_deleted_session_404(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    _add_turn(db, session_id, "问", "答")
    token = client.post(f"/api/sessions/{session_id}/share").json()["token"]
    client.delete(f"/api/sessions/{session_id}")
    client.cookies.clear()
    r = client.get(f"/api/shares/{token}")
    assert r.status_code == 404


def test_turn_share_question_without_answer(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    user = Message(
        session_id=session_id,
        role="user",
        content="只有问",
        model_name="Display",
        model="api-id",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = client.post(
        f"/api/sessions/{session_id}/share/turn",
        json={"user_message_id": user.id},
    ).json()["token"]
    client.cookies.clear()
    data = client.get(f"/api/shares/{token}").json()
    assert data["kind"] == "turn"
    assert [m["content"] for m in data["messages"]] == ["只有问"]


def test_turn_share_rejects_foreign_message(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    user, _ = _add_turn(db, a, "问", "答")
    r = client.post(
        f"/api/sessions/{b}/share/turn",
        json={"user_message_id": user.id},
    )
    assert r.status_code == 400
