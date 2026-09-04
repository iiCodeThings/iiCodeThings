from app.db import seed_default_user
from app.security import hash_password


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_models_crud_masks_key(client, db, settings):
    _login(client, db, settings)
    r = client.post(
        "/api/models",
        json={
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk-abcdefghij",
            "model": "deepseek-chat",
            "supports_vision": False,
            "sort_order": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["api_key_masked"] == "****ghij"
    assert "api_key" not in body or body.get("api_key") in (None, body["api_key_masked"])

    listed = client.get("/api/models").json()
    assert listed[0]["name"] == "DeepSeek"
    assert listed[0]["api_key_masked"].startswith("****")
