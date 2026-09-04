from pathlib import Path

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.db import get_engine, init_db, init_session_factory, seed_default_user
from app.security import hash_password


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    engine = get_engine(settings)
    init_db(engine)
    init_session_factory(engine)

    app = FastAPI(title="iiCode Chat")
    app.state.settings = settings
    app.state.engine = engine

    from app.routers import auth as auth_router
    from app.routers import llm_models as llm_models_router
    from app.routers import sessions as sessions_router

    app.include_router(auth_router.router)
    app.include_router(llm_models_router.router)
    app.include_router(sessions_router.router)

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        seed_default_user(
            db, settings.app_username, hash_password(settings.app_password)
        )
    finally:
        db.close()
    return app
