import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import get_db, get_engine, init_db
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        app_username="admin",
        app_password="passpass",
        session_secret="secret-secret-secret-secret",
        database_url=f"sqlite:///{tmp_path}/test.db",
        upload_dir=str(tmp_path / "uploads"),
    )


@pytest.fixture
def engine(settings):
    engine = get_engine(settings)
    init_db(engine)
    return engine


@pytest.fixture
def db(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(settings, engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app(settings)

    def _get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
