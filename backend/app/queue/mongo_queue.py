from datetime import datetime, timedelta
from typing import Any

from pymongo import ReturnDocument

from app.db.mongo import Database
from app.models.common import new_id, utcnow
from app.queue.base import Job, JobQueue


class MongoJobQueue(JobQueue):
    def __init__(self, db: Database, claim_timeout_s: int = 300, max_attempts: int = 2,
                 retention_days: int = 7):  # fmt: skip
        self.col = db.jobs
        self.claim_timeout = timedelta(seconds=claim_timeout_s)
        self.max_attempts = max_attempts
        self.retention = timedelta(days=retention_days)

    async def enqueue(
        self, task_id: str, payload: dict[str, Any] | None = None, delay_s: float = 0
    ) -> str:
        now = utcnow()
        job_id = new_id()
        await self.col.insert_one(
            {
                "_id": job_id,
                "task_id": task_id,
                "payload": payload or {},
                "state": "ready",
                "attempts": 0,
                "claimed_by": None,
                "claimed_at": None,
                "run_after": now + timedelta(seconds=delay_s),
                "created_at": now,
                "expires_at": now + self.retention,
            }
        )
        return job_id

    async def claim(self, worker_id: str) -> Job | None:
        # Under contention find_one_and_update can come back empty when the document it was
        # about to take is claimed by someone else first; retry while claimable jobs remain.
        for _ in range(5):
            job = await self._claim_once(worker_id)
            if job is not None:
                return job
            if await self.col.find_one(self._claimable(utcnow()), {"_id": 1}) is None:
                return None
        return None

    def _claimable(self, now: datetime) -> dict[str, Any]:
        return {
            "attempts": {"$lt": self.max_attempts},
            "$or": [
                {"state": "ready", "run_after": {"$lte": now}},
                # stale claim: the worker stopped heart-beating (crash / restart)
                {"state": "claimed", "claimed_at": {"$lt": now - self.claim_timeout}},
            ],
        }

    async def _claim_once(self, worker_id: str) -> Job | None:
        now = utcnow()
        doc = await self.col.find_one_and_update(
            self._claimable(now),
            {
                "$set": {"state": "claimed", "claimed_by": worker_id, "claimed_at": now},
                "$inc": {"attempts": 1},
            },
            sort=[("run_after", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            return None
        return Job(
            id=doc["_id"],
            task_id=doc["task_id"],
            attempts=doc["attempts"],
            payload=doc.get("payload") or {},
        )

    async def heartbeat(self, job_id: str, worker_id: str) -> bool:
        res = await self.col.update_one(
            {"_id": job_id, "state": "claimed", "claimed_by": worker_id},
            {"$set": {"claimed_at": utcnow()}},
        )
        return res.modified_count == 1

    async def complete(self, job_id: str, worker_id: str) -> None:
        await self.col.update_one(
            {"_id": job_id, "claimed_by": worker_id},
            {"$set": {"state": "done", "finished_at": utcnow()}, "$unset": {"payload": ""}},
        )

    async def fail(self, job_id: str, worker_id: str, retry_in_s: float | None = None) -> None:
        if retry_in_s is not None:
            update = {
                "state": "ready",
                "claimed_by": None,
                "run_after": utcnow() + timedelta(seconds=retry_in_s),
            }
        else:
            update = {"state": "failed", "finished_at": utcnow()}
        ops: dict[str, Any] = {"$set": update}
        if retry_in_s is None:
            ops["$unset"] = {"payload": ""}
        await self.col.update_one({"_id": job_id, "claimed_by": worker_id}, ops)

    async def depth(self) -> int:
        return await self.col.count_documents({"state": "ready"})

    async def exhausted(self) -> list[str]:
        now = utcnow()
        stale = {
            "attempts": {"$gte": self.max_attempts},
            "state": "claimed",
            "claimed_at": {"$lt": now - self.claim_timeout},
        }
        task_ids = [d["task_id"] async for d in self.col.find(stale, {"task_id": 1})]
        if task_ids:
            await self.col.update_many(
                stale, {"$set": {"state": "failed", "finished_at": now}, "$unset": {"payload": ""}}
            )
        return task_ids
