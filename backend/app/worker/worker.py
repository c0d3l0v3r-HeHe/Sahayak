"""Worker: claims jobs from the queue and runs flows in isolated browser contexts."""

import asyncio
import logging
import os
import socket
from dataclasses import replace

from app.core.config import Settings
from app.db.mongo import Database
from app.engine.base import BrowserEngine
from app.flows.registry import FlowRegistry
from app.flows.runner import (
    MSG_CANCELLED,
    MSG_SITE_CHANGED,
    MSG_TIMEOUT,
    FlowFailed,
    FlowRunner,
    HandoffExpired,
    RunnerConfig,
    TaskCancelled,
)
from app.handoff.service import HandoffService
from app.models.common import LocalizedText
from app.models.task import TERMINAL, EventType, TaskStatus
from app.queue.base import Job, JobQueue
from app.queue.mongo_queue import MongoJobQueue
from app.services.screens import ScreenStore
from app.services.tasks import TaskService
from app.worker.context import TaskRunContext
from app.worker.pool import BrowserPool

log = logging.getLogger(__name__)

MSG_RESTART = LocalizedText(
    en="Something went wrong on our side. Starting again…",
    hi="हमारी तरफ़ कुछ गड़बड़ हुई। फिर से शुरू कर रहे हैं…",
)
MSG_WORKER_LOST = LocalizedText(
    en="Sorry, something went wrong on our side. Please try again.",
    hi="माफ़ कीजिए, हमारी तरफ़ कुछ गड़बड़ हुई। कृपया फिर से कोशिश करें।",
)


def detect_worker_url(settings: Settings) -> str:
    if settings.worker_internal_url:
        return settings.worker_internal_url.rstrip("/")
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = "127.0.0.1"
    return f"http://{ip}:{settings.worker_internal_port}"


class Worker:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        engine: BrowserEngine,
        registry: FlowRegistry,
        worker_url: str,
        queue: JobQueue | None = None,
    ):
        self.settings = settings
        self.db = db
        self.registry = registry
        self.worker_url = worker_url
        self.id = f"{socket.gethostname()}-{os.getpid()}"
        self.queue = queue or MongoJobQueue(
            db, settings.job_claim_timeout_s, settings.job_max_attempts, settings.task_ttl_days
        )
        self.tasks = TaskService(db, settings.task_ttl_days)
        self.handoffs = HandoffService(db, settings.handoff_ttl_minutes)
        self.screens = ScreenStore(settings.screenshot_dir)
        self.pool = BrowserPool(engine, settings.worker_concurrency, settings.per_site_concurrency)
        self.runner_config = RunnerConfig(
            demo_mode=settings.demo_mode,
            mock_sites_url=settings.mock_sites_url,
            delay_min_ms=settings.action_delay_min_ms,
            delay_max_ms=settings.action_delay_max_ms,
            step_retries=settings.step_retries,
            handoff_timeout_s=settings.handoff_timeout_s,
        )
        self._stop = asyncio.Event()
        self.poll_interval_s = 0.5

    async def run_forever(self) -> None:
        await self.pool.start()
        log.info("worker %s started (%d slots)", self.id, self.pool.concurrency)
        slots = [asyncio.create_task(self._slot_loop(i)) for i in range(self.pool.concurrency)]
        maintenance = asyncio.create_task(self._maintenance_loop())
        try:
            await self._stop.wait()
        finally:
            for t in [*slots, maintenance]:
                t.cancel()
            await asyncio.gather(*slots, maintenance, return_exceptions=True)
            await self.pool.stop()

    def stop(self) -> None:
        self._stop.set()

    async def _slot_loop(self, slot: int) -> None:
        while not self._stop.is_set():
            try:
                job = await self.queue.claim(self.id)
            except Exception:
                log.exception("claim failed")
                job = None
            if job is None:
                await asyncio.sleep(self.poll_interval_s)
                continue
            await self.process(job)

    async def _maintenance_loop(self) -> None:
        while not self._stop.is_set():
            try:
                for task_id in await self.queue.exhausted():
                    await self.tasks.add_event(task_id, EventType.error, MSG_WORKER_LOST)
                    await self.tasks.set_status(
                        task_id, TaskStatus.failed, error=MSG_WORKER_LOST.model_dump()
                    )
                await self._sweep_screens()
            except Exception:
                log.exception("maintenance failed")
            await asyncio.sleep(60)

    async def _sweep_screens(self) -> None:
        root = self.screens.root
        if not root.exists():
            return
        names = [p.name for p in root.iterdir() if p.is_dir()]
        live = {d["_id"] async for d in self.db.tasks.find({"_id": {"$in": names}}, {"_id": 1})}
        self.screens.sweep(live, max_age_s=self.settings.task_ttl_days * 86400)

    async def _heartbeat(self, job: Job) -> None:
        interval = max(1.0, self.settings.job_claim_timeout_s / 3)
        while True:
            await asyncio.sleep(interval)
            await self.queue.heartbeat(job.id, self.id)

    async def process(self, job: Job) -> None:
        heartbeat = asyncio.create_task(self._heartbeat(job))
        try:
            await self._process(job)
        except Exception:
            log.exception("unexpected error in task %s", job.task_id)
            await self.tasks.add_event(job.task_id, EventType.error, MSG_WORKER_LOST)
            await self.tasks.set_status(
                job.task_id, TaskStatus.failed, error=MSG_WORKER_LOST.model_dump()
            )
        finally:
            heartbeat.cancel()
            await self.queue.complete(job.id, self.id)

    async def _process(self, job: Job) -> None:
        task = await self.tasks.get(job.task_id)
        if task is None or TaskStatus(task["status"]) in TERMINAL:
            return
        task_id = task["_id"]
        if task.get("cancel_requested"):
            await self.tasks.set_status(task_id, TaskStatus.cancelled)
            return
        flow = self.registry.get(task["flow_id"])
        if flow is None:
            await self.tasks.set_status(
                task_id, TaskStatus.failed, error=MSG_SITE_CHANGED.model_dump()
            )
            return
        if task["status"] != TaskStatus.queued.value:  # picked up again after a worker crash
            await self.tasks.set_status(task_id, TaskStatus.queued)
            await self.tasks.add_event(task_id, EventType.step, MSG_RESTART)
        params = job.payload.get("params", {})
        cfg = replace(self.runner_config, lang=task.get("lang", "en"))

        ctx = TaskRunContext(task_id, self.tasks, self.screens, self.handoffs, self.worker_url)
        async with self.pool.slot(flow.site) as engine:
            await self.tasks.set_status(task_id, TaskStatus.running)
            runner = FlowRunner(engine, cfg)
            try:
                result = await runner.run(flow, params, ctx)
            except FlowFailed as exc:
                log.info("task %s failed: %s", task_id, exc.detail)
                await self.tasks.add_event(task_id, EventType.error, exc.message)
                await self.tasks.set_status(
                    task_id, TaskStatus.failed, error=exc.message.model_dump()
                )
                return
            except TaskCancelled:
                await self.tasks.add_event(task_id, EventType.step, MSG_CANCELLED)
                await self.tasks.set_status(task_id, TaskStatus.cancelled)
                return
            except HandoffExpired:
                await self.tasks.add_event(task_id, EventType.error, MSG_TIMEOUT)
                await self.tasks.set_status(
                    task_id, TaskStatus.expired, error=MSG_TIMEOUT.model_dump()
                )
                return
        payload = result.to_dict()
        await self.tasks.add_event(task_id, EventType.result, result=payload)
        if not await self.tasks.set_status(task_id, TaskStatus.succeeded, result=payload):
            log.info("task %s finished but was already closed", task_id)
