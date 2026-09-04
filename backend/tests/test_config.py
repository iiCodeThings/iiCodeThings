import pytest
from pydantic import ValidationError

from app.config import Settings, load_settings


def test_settings_accepts_required_fields():
    s = Settings(
        _env_file=None,
        app_username="admin",
        app_password="pass",
        session_secret="secret-secret-secret-secret",
    )
    assert s.mysql_host == "127.0.0.1"
    assert s.mysql_user == "root"
    assert s.mysql_password == ""
    assert s.mysql_database == "chat_db"
    assert s.max_upload_bytes == 20 * 1024 * 1024


def test_load_settings_exits_when_secret_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_USERNAME", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(SystemExit):
        load_settings()
