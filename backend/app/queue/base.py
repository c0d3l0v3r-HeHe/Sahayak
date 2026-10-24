"""Job queue interface. MongoJobQueue is the default; a Redis implementation can drop in."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    task_id: str
    attempts: int
    payload: dict[str, Any] = field(default_factory=dict)


class JobQueue(ABC):
    @abstractmethod
    async def enqueue(
        self, task_id: str, payload: dict[str, Any] | None = None, delay_s: float = 0
    ) -> str:
        """`payload` holds the real task parameters; it is removed when the job finishes."""

    @abstractmethod
    async def claim(self, worker_id: str) -> Job | None:
        """Atomically claim the next ready job (or a stale one from a crashed worker)."""

    @abstractmethod
    async def heartbeat(self, job_id: str, worker_id: str) -> bool: ...

    @abstractmethod
    async def complete(self, job_id: str, worker_id: str) -> None: ...

    @abstractmethod
    async def fail(self, job_id: str, worker_id: str, retry_in_s: float | None = None) -> None: ...

    @abstractmethod
    async def depth(self) -> int:
        """Number of jobs waiting to run."""

    @abstractmethod
    async def exhausted(self) -> list[str]:
        """Task ids whose jobs were abandoned too many times; marks them failed."""
