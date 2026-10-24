"""Worker entrypoint: `python -m app.worker.main`."""

import asyncio
import contextlib
import logging
import signal

import uvicorn

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.mongo import connect, ensure_indexes
from app.engine.factory import create_engine
from app.flows.registry import get_registry
from app.worker.internal import create_internal_app
from app.worker.worker import Worker, detect_worker_url

log = logging.getLogger("app.worker")


class _QuietServer(uvicorn.Server):
    """The worker owns signal handling; uvicorn must not install its own."""

    def capture_signals(self):  # type: ignore[override]
        return contextlib.nullcontext()


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    db = connect(settings)
    await ensure_indexes(db)
    registry = get_registry()
    worker = Worker(settings, db, create_engine(settings), registry, detect_worker_url(settings))

    server = _QuietServer(
        uvicorn.Config(
            create_internal_app(),
            host="0.0.0.0",
            port=settings.worker_internal_port,
            log_level="warning",
            access_log=False,
        )
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop)

    log.info("worker reachable at %s", worker.worker_url)
    server_task = asyncio.create_task(server.serve())
    try:
        await worker.run_forever()
    finally:
        server.should_exit = True
        await server_task
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
