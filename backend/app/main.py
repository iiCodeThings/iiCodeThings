from fastapi import FastAPI

from app.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="iiCode Chat")
    app.state.settings = settings
    return app
