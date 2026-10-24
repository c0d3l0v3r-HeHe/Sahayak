"""RunContext implementation that records progress in Mongo for the API / app to show."""

from typing import Any

from app.flows.runner import RunContext
from app.handoff.service import HandoffService
from app.models.common import LocalizedText
from app.models.task import EventType, TaskStatus
from app.services.screens import ScreenStore
from app.services.tasks import TaskService


class TaskRunContext(RunContext):
    def __init__(
        self,
        task_id: str,
        tasks: TaskService,
        screens: ScreenStore,
        handoffs: HandoffService,
        worker_url: str,
    ):
        self.task_id = task_id
        self.tasks = tasks
        self.screens = screens
        self.handoffs = handoffs
        self.worker_url = worker_url

    async def step(self, message: LocalizedText) -> None:
        await self.tasks.add_event(self.task_id, EventType.step, message)

    async def screenshot(self, image: bytes) -> str:
        shot_id = self.screens.save(self.task_id, image)
        await self.tasks.add_event(self.task_id, EventType.screenshot, screenshot_id=shot_id)
        return shot_id

    async def ask(
        self,
        kind: str,
        prompt: LocalizedText,
        image_id: str | None,
        param: str | None,
        timeout_s: float,
    ) -> str:
        doc, fut = await self.handoffs.open(
            self.task_id, kind, prompt, timeout_s, self.worker_url, image_id=image_id, param=param
        )
        public: dict[str, Any] = {
            "id": doc["_id"],
            "kind": kind,
            "prompt": doc["prompt"],
            "image_id": image_id,
            "param": param,
            "expires_at": doc["expires_at"],
        }
        await self.tasks.set_status(self.task_id, TaskStatus.awaiting_user)
        await self.tasks.add_event(self.task_id, EventType.handoff_required, handoff=public)
        try:
            value = await self.handoffs.wait(doc["_id"], fut, timeout_s)
        finally:
            await self.tasks.add_event(
                self.task_id, EventType.handoff_resolved, handoff={"id": doc["_id"], "kind": kind}
            )
        await self.tasks.set_status(self.task_id, TaskStatus.running)
        return value

    async def cancelled(self) -> bool:
        return await self.tasks.is_cancel_requested(self.task_id)
