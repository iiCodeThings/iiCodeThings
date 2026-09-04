from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    app_username: str = Field(validation_alias="APP_USERNAME")
    app_password: str = Field(validation_alias="APP_PASSWORD")
    session_secret: str = Field(validation_alias="SESSION_SECRET")
    mysql_host: str = Field(default="127.0.0.1", validation_alias="MYSQL_HOST")
    mysql_user: str = Field(default="root", validation_alias="MYSQL_USER")
    mysql_password: str = Field(default="", validation_alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="chat_db", validation_alias="MYSQL_DATABASE")
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    upload_dir: str = Field(
        default="/var/lib/iicode-chat/uploads", validation_alias="UPLOAD_DIR"
    )
    max_upload_bytes: int = Field(
        default=20 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES"
    )
    cookie_name: str = "chat_session"
    cookie_max_age: int = 60 * 60 * 24 * 30


def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:
        raise SystemExit(f"missing required settings: {exc}") from exc
