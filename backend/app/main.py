"""FastAPI application factory."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import AppState
from app.api.v1 import auth, flows, intent, tasks
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.db.mongo import connect, ensure_indexes
from app.flows.registry import FlowRegistry, get_registry
from app.handoff.service import LOCAL, HandoffService
from app.queue.mongo_queue import MongoJobQueue
from app.services.screens import ScreenStore
from app.services.tasks import TaskService

log = logging.getLogger("app")


def create_app(settings: Settings | None = None, registry: FlowRegistry | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = connect(settings)
        reg = registry or get_registry()
        try:
            await ensure_indexes(db)
            await reg.sync_to_db(db)
        except Exception as exc:  # keep the API up (e.g. /health, mock sites) without Mongo
            log.error("MongoDB not ready: %s", exc)
        queue = MongoJobQueue(
            db, settings.job_claim_timeout_s, settings.job_max_attempts, settings.task_ttl_days
        )
        app.state.sahayak = AppState(
            settings=settings,
            db=db,
            registry=reg,
            tasks=TaskService(db, settings.task_ttl_days),
            handoffs=HandoffService(db, settings.handoff_ttl_minutes),
            queue=queue,
            screens=ScreenStore(settings.screenshot_dir),
        )
        worker_task = None
        if settings.embedded_worker:
            from app.engine.factory import create_engine
            from app.worker.worker import Worker

            worker = Worker(settings, db, create_engine(settings), reg, LOCAL, queue=queue)
            worker_task = asyncio.create_task(worker.run_forever())
            app.state.worker = worker
        try:
            yield
        finally:
            if worker_task:
                app.state.worker.stop()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(worker_task, timeout=10)
            await db.close()

    app = FastAPI(title="Sahayak API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (auth.router, flows.router, intent.router, tasks.router):
        app.include_router(router, prefix="/v1")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "demo_mode": settings.demo_mode}

    if settings.serve_mock_sites:
        from mock_sites.server import create_mock_app

        app.mount("/mock", create_mock_app(settings))

    return app


app = create_app()
