"""FastAPI application factory."""

from fastapi import FastAPI

from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Sahayak API", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "demo_mode": settings.demo_mode}

    return app


app = create_app()
