from datetime import datetime, timedelta

from app.db import seed_default_user
from app.security import hash_password
from app.tables import ChatSession


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_list_orders_pinned_first_then_updated_at(client, db, settings):
    _login(client, db, settings)
    older = client.post("/api/sessions").json()["id"]
    newer = client.post("/api/sessions").json()["id"]
    pinned = client.post("/api/sessions").json()["id"]
    db.expire_all()
    t0 = datetime.utcnow() - timedelta(days=2)
    t1 = datetime.utcnow() - timedelta(days=1)
    tpin = datetime.utcnow()
    db.query(ChatSession).filter(ChatSession.id == older).update(
        {"updated_at": t0, "title": "旧"}
    )
    db.query(ChatSession).filter(ChatSession.id == newer).update(
        {"updated_at": t1, "title": "新"}
    )
    db.query(ChatSession).filter(ChatSession.id == pinned).update(
        {"updated_at": t0, "pinned_at": tpin, "title": "钉"}
    )
    db.commit()
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[0] == pinned
    assert ids[1] == newer
    assert ids[2] == older
    flags = {s["id"]: s["pinned"] for s in client.get("/api/sessions").json()}
    assert flags[pinned] is True
    assert flags[newer] is False


def test_pin_unauthenticated(client):
    r = client.post("/api/sessions/1/pin")
    assert r.status_code == 401


def test_pin_deleted_404(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    client.delete(f"/api/sessions/{session_id}")
    r = client.post(f"/api/sessions/{session_id}/pin")
    assert r.status_code == 404
    assert r.json()["detail"] == "会话不存在"
    r = client.delete(f"/api/sessions/{session_id}/pin")
    assert r.status_code == 404


def test_pin_bump_order_keeps_updated_at(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    db.expire_all()
    old_a = datetime.utcnow() - timedelta(days=5)
    db.query(ChatSession).filter(ChatSession.id == a).update({"updated_at": old_a})
    db.query(ChatSession).filter(ChatSession.id == b).update({"updated_at": old_a})
    db.commit()
    assert client.post(f"/api/sessions/{a}/pin").status_code == 200
    assert client.post(f"/api/sessions/{b}/pin").json()["pinned"] is True
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[:2] == [b, a]
    r = client.post(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[0] == a
    db.expire_all()
    row = db.get(ChatSession, a)
    assert abs((row.updated_at - old_a).total_seconds()) < 2


def test_unpin_returns_to_updated_order(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    client.post(f"/api/sessions/{a}/pin")
    r = client.delete(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    assert r.json()["pinned"] is False
    r = client.delete(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert a in ids and b in ids
    assert ids.index(b) < ids.index(a)
