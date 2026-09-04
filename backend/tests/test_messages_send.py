from app.db import seed_default_user
from app.security import hash_password
from app.services.llm import StreamEvent
from app.tables import LlmModel, Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_send_message_unauthenticated(client):
    r = client.post("/api/sessions/1/messages", data={"content": "hi"})
    assert r.status_code == 401


def test_send_message_no_model_returns_400(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{session_id}/messages",
        data={"content": "hello"},
    )
    assert r.status_code == 400


def test_send_message_empty_content_and_no_files_returns_400(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    model = LlmModel(
        name="Display",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-id",
        supports_vision=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    r = client.post(
        f"/api/sessions/{session_id}/messages",
        data={"content": "", "model_id": str(model.id)},
    )
    assert r.status_code == 400


def test_send_message_persists_user_and_assistant(client, db, settings, monkeypatch):
    async def fake_stream(**kwargs):
        yield StreamEvent(kind="delta", text="hello")
        yield StreamEvent(kind="done")

    monkeypatch.setattr("app.routers.messages.stream_chat_completion", fake_stream)

    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    model = LlmModel(
        name="展示名",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-model-id",
        supports_vision=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    r = client.post(
        f"/api/sessions/{session_id}/messages",
        data={"content": "hi there", "model_id": str(model.id)},
    )
    assert r.status_code == 200

    db.expire_all()
    msgs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )
    assert len(msgs) == 2
    user_msg, assistant_msg = msgs
    assert user_msg.role == "user"
    assert user_msg.content == "hi there"
    assert user_msg.model_name == "展示名"
    assert user_msg.model == "api-model-id"
    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "hello"
    assert assistant_msg.model_name == "展示名"
    assert assistant_msg.model == "api-model-id"
