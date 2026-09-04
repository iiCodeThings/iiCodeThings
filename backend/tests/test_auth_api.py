from app.db import seed_default_user
from app.security import hash_password


def test_login_rejects_wrong_password(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    r = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "用户名或密码错误"


def test_login_logout_and_password_change(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    r = client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})
    assert r.status_code == 200
    assert client.cookies.get("chat_session")

    r = client.post(
        "/api/auth/password",
        json={"old_password": "passpass", "new_password": "newpass1"},
    )
    assert r.status_code == 200

    r = client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})
    assert r.status_code == 401

    r = client.post("/api/auth/login", json={"username": "admin", "password": "newpass1"})
    assert r.status_code == 200
