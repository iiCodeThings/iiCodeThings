from app.db import seed_default_user
from app.security import hash_password
from app.services.turns import find_turn, public_message
from app.tables import ChatSession, Message, Share


def _session(db, title="韦伯笔记"):
    row = ChatSession(title=title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def _msg(db, session_id, role, content, reasoning=None):
    m = Message(
        session_id=session_id,
        role=role,
        content=content,
        reasoning=reasoning,
        model_name="Display",
        model="api-id",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_find_turn_from_user_or_assistant_is_same_pair(db):
    s = _session(db)
    q = _msg(db, s.id, "user", "韦伯是谁？")
    a = _msg(db, s.id, "assistant", "一位社会学家。", reasoning="secret")
    from_user = find_turn(db, s.id, q.id)
    from_asst = find_turn(db, s.id, a.id)
    assert from_user is not None and from_asst is not None
    assert from_user[0].id == from_asst[0].id == q.id
    assert from_user[1].id == from_asst[1].id == a.id


def test_find_turn_question_without_answer(db):
    s = _session(db)
    q = _msg(db, s.id, "user", "只有问")
    found = find_turn(db, s.id, q.id)
    assert found is not None
    assert found[0].id == q.id
    assert found[1] is None


def test_find_turn_missing_or_wrong_session(db):
    a = _session(db)
    b = _session(db)
    q = _msg(db, a.id, "user", "问")
    assert find_turn(db, a.id, 99999) is None
    assert find_turn(db, b.id, q.id) is None


def test_find_turn_assistant_without_user(db):
    s = _session(db)
    a = _msg(db, s.id, "assistant", "孤儿答")
    assert find_turn(db, s.id, a.id) is None


def test_public_message_omits_reasoning(db):
    s = _session(db)
    a = _msg(db, s.id, "assistant", "答", reasoning="secret")
    out = public_message(a)
    assert out["role"] == "assistant"
    assert out["content"] == "答"
    assert out["model_name"] == "Display"
    assert "reasoning" not in out
    assert out["attachments"] == []


def test_get_turn_from_user_or_assistant(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    client.patch(f"/api/sessions/{session_id}", json={"title": "韦伯笔记"})
    q = _msg(db, session_id, "user", "韦伯是谁？")
    a = _msg(db, session_id, "assistant", "一位社会学家。", reasoning="secret")

    via_q = client.get(f"/api/sessions/{session_id}/turns/{q.id}")
    via_a = client.get(f"/api/sessions/{session_id}/turns/{a.id}")
    assert via_q.status_code == 200
    assert via_a.status_code == 200
    assert via_q.json()["kind"] == "turn"
    assert via_q.json()["title"] == "韦伯笔记"
    assert via_q.json()["user_message_id"] == via_a.json()["user_message_id"] == q.id
    assert [m["content"] for m in via_q.json()["messages"]] == ["韦伯是谁？", "一位社会学家。"]
    assert via_q.json()["messages"] == via_a.json()["messages"]
    assert "reasoning" not in via_q.json()["messages"][1]
    assert db.query(Share).count() == 0


def test_get_turn_question_only(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    q = _msg(db, session_id, "user", "只有问")
    r = client.get(f"/api/sessions/{session_id}/turns/{q.id}")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 1
    assert r.json()["user_message_id"] == q.id


def test_get_turn_requires_login(client, db):
    s = _session(db)
    q = _msg(db, s.id, "user", "问")
    r = client.get(f"/api/sessions/{s.id}/turns/{q.id}")
    assert r.status_code in (401, 403)


def test_get_turn_404s(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    q = _msg(db, a, "user", "问")
    lone = client.post("/api/sessions").json()["id"]
    orphan = _msg(db, lone, "assistant", "孤儿答")
    assert client.get(f"/api/sessions/{a}/turns/99999").status_code == 404
    wrong = client.get(f"/api/sessions/{b}/turns/{q.id}")
    assert wrong.status_code == 404
    assert wrong.json()["detail"] == "这一轮不存在"
    missing_user = client.get(f"/api/sessions/{lone}/turns/{orphan.id}")
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"] == "这一轮不存在"
    client.delete(f"/api/sessions/{a}")
    gone = client.get(f"/api/sessions/{a}/turns/{q.id}")
    assert gone.status_code == 404
    assert gone.json()["detail"] == "会话不存在"
