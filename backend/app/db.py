from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.tables import Base, User


def mysql_url(settings: Settings) -> str:
    password = settings.mysql_password
    auth = settings.mysql_user if password == "" else f"{settings.mysql_user}:{password}"
    return f"mysql+pymysql://{auth}@{settings.mysql_host}/{settings.mysql_database}?charset=utf8mb4"


def get_engine(settings: Settings) -> Engine:
    url = settings.database_url or mysql_url(settings)
    kwargs = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


SessionLocal: sessionmaker[Session] | None = None


def init_session_factory(engine: Engine) -> sessionmaker[Session]:
    global SessionLocal
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal


def migrate_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("sessions")}
    if "deleted_at" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN deleted_at DATETIME"))


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    migrate_schema(engine)


def seed_default_user(db: Session, username: str, password_hash: str) -> None:
    if db.query(User).count() == 0:
        db.add(User(username=username, password_hash=password_hash, token_version=0))
        db.commit()


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("SessionLocal not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
