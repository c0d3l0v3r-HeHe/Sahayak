from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.common import LocalizedText


class TaskStatus(StrEnum):
    queued = "queued"
    running = "running"
    awaiting_user = "awaiting_user"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"


TERMINAL = {TaskStatus.succeeded, TaskStatus.failed, TaskStatus.cancelled, TaskStatus.expired}

TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.queued: {TaskStatus.running, TaskStatus.cancelled, TaskStatus.failed},
    TaskStatus.running: {
        TaskStatus.awaiting_user,
        TaskStatus.succeeded,
        TaskStatus.failed,
        TaskStatus.cancelled,
        TaskStatus.queued,  # re-queued after a worker crash
    },
    TaskStatus.awaiting_user: {
        TaskStatus.running,
        TaskStatus.cancelled,
        TaskStatus.expired,
        TaskStatus.failed,
        TaskStatus.queued,
    },
}


class EventType(StrEnum):
    step = "step"
    screenshot = "screenshot"
    handoff_required = "handoff_required"
    handoff_resolved = "handoff_resolved"
    result = "result"
    error = "error"
    status = "status"


class TaskEvent(BaseModel):
    seq: int
    ts: datetime
    type: EventType
    message: LocalizedText | None = None
    screenshot_id: str | None = None
    status: TaskStatus | None = None
    handoff: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class TaskCreate(BaseModel):
    flow_id: str
    params: dict[str, str] = Field(default_factory=dict)


class HandoffAnswer(BaseModel):
    handoff_id: str
    # The answer is forwarded to the waiting worker and never stored or logged.
    value: str = Field(max_length=200, repr=False)
