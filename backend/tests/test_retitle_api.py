from datetime import datetime, timedelta

from app.db import seed_default_user
from app.security import hash_password
from app.tables import Attachment, ChatSession, LlmModel, Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def _model(db) -> LlmModel:
    row = LlmModel(
        name="Display",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-id",
        supports_vision=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_retitle_unauthenticated(client):
    r = client.post("/api/sessions/1/retitle", json={"model_id": 1})
    assert r.status_code == 401


def test_retitle_missing_model_400(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": 999})
    assert r.status_code == 400
    assert r.json()["detail"] == "请先在设置中添加模型"


def test_retitle_deleted_session_404(client, db, settings):
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    client.delete(f"/api/sessions/{session_id}")
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 404
    assert r.json()["detail"] == "会话不存在"


def test_retitle_empty_session_skipped(client, db, settings, monkeypatch):
    called = {"n": 0}

    async def boom(**kwargs):
        called["n"] += 1
        raise AssertionError("should not call")

    monkeypatch.setattr("app.routers.sessions.generate_session_title", boom)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    assert r.json() == {"skipped": True, "reason": "no_messages"}
    assert called["n"] == 0
    db.expire_all()
    assert db.get(ChatSession, session_id).title == "新对话"


def test_retitle_success_keeps_updated_at(client, db, settings, monkeypatch):
    async def fake_generate(**kwargs):
        assert kwargs["turns"][0]["content"] == "韦伯"
        assert "internal" not in kwargs["turns"][0]["content"]
        return "韦伯与正当性"

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    db.expire_all()
    session = db.get(ChatSession, session_id)
    old_updated = datetime.utcnow() - timedelta(days=3)
    session.updated_at = old_updated
    session.title = "旧标题"
    db.add(
        Message(
            session_id=session_id,
            role="user",
            content="韦伯",
            reasoning="internal",
            model_name="Display",
            model="api-id",
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "韦伯与正当性"
    db.expire_all()
    row = db.get(ChatSession, session_id)
    assert row.title == "韦伯与正当性"
    assert abs((row.updated_at - old_updated).total_seconds()) < 2


def test_retitle_omits_reasoning_includes_doc_not_image(client, db, settings, monkeypatch):
    captured = {}

    async def fake_generate(**kwargs):
        captured["turns"] = kwargs["turns"]
        return "笔记摘要"

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    msg = Message(
        session_id=session_id,
        role="user",
        content="看这个",
        reasoning="secret-reasoning",
        model_name="Display",
        model="api-id",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    db.add(
        Attachment(
            message_id=msg.id,
            kind="document",
            original_filename="note.md",
            mime_type="text/markdown",
            storage_path="/tmp/note.md",
            extracted_text="人类学笔记",
        )
    )
    db.add(
        Attachment(
            message_id=msg.id,
            kind="image",
            original_filename="a.png",
            mime_type="image/png",
            storage_path="/tmp/a.png",
            extracted_text=None,
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    blob = captured["turns"][0]["content"]
    assert "人类学笔记" in blob
    assert "secret-reasoning" not in blob
    assert "/tmp/a.png" not in blob


def test_retitle_upstream_error_502(client, db, settings, monkeypatch):
    async def fake_generate(**kwargs):
        from app.services.retitle import TitleGenerationError

        raise TitleGenerationError("上游挂了")

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    db.add(
        Message(
            session_id=session_id,
            role="user",
            content="hi",
            model_name="Display",
            model="api-id",
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 502
    assert r.json()["detail"] == "上游挂了"
    db.expire_all()
    assert db.get(ChatSession, session_id).title == "新对话"
