"""Task persistence, events and the status state machine."""

from datetime import timedelta
from typing import Any

from pymongo import ReturnDocument

from app.db.mongo import Database
from app.models.common import LocalizedText, new_id, utcnow
from app.models.flow import FlowDefinition
from app.models.task import TERMINAL, TRANSITIONS, EventType, TaskStatus

MAX_EVENTS = 300


class TaskService:
    def __init__(self, db: Database, ttl_days: int = 7):
        self.db = db
        self.ttl = timedelta(days=ttl_days)

    async def create(
        self, user_id: str, flow: FlowDefinition, display_params: dict[str, str], lang: str
    ) -> str:
        now = utcnow()
        task_id = new_id()
        await self.db.tasks.insert_one(
            {
                "_id": task_id,
                "user_id": user_id,
                "flow_id": flow.id,
                "flow_version": flow.version,
                "title": flow.title.model_dump(),
                "params": display_params,  # redacted copy, for display only
                "lang": lang,
                "status": TaskStatus.queued.value,
                "events": [],
                "event_seq": 0,
                "result": None,
                "error": None,
                "cancel_requested": False,
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "expires_at": now + self.ttl,
            }
        )
        await self.add_event(task_id, EventType.status, status=TaskStatus.queued)
        return task_id

    async def get(self, task_id: str) -> dict[str, Any] | None:
        return await self.db.tasks.find_one({"_id": task_id})

    async def list_for_user(self, user_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        cursor = (
            self.db.tasks.find({"user_id": user_id}, {"events": 0})
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    async def add_event(
        self,
        task_id: str,
        type: EventType,
        message: LocalizedText | dict[str, str] | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        doc = await self.db.tasks.find_one_and_update(
            {"_id": task_id},
            {"$inc": {"event_seq": 1}},
            projection={"event_seq": 1},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            return None
        event: dict[str, Any] = {"seq": doc["event_seq"], "ts": utcnow(), "type": type.value}
        if message is not None:
            event["message"] = (
                message.model_dump() if isinstance(message, LocalizedText) else dict(message)
            )
        for key, value in fields.items():
            if value is not None:
                event[key] = value.value if isinstance(value, TaskStatus) else value
        await self.db.tasks.update_one(
            {"_id": task_id}, {"$push": {"events": {"$each": [event], "$slice": -MAX_EVENTS}}}
        )
        return event

    async def set_status(self, task_id: str, status: TaskStatus, **extra: Any) -> bool:
        allowed_from = [s.value for s, targets in TRANSITIONS.items() if status in targets]
        update: dict[str, Any] = {"status": status.value, **extra}
        now = utcnow()
        if status == TaskStatus.running:
            update.setdefault("started_at", now)
        if status in TERMINAL:
            update["finished_at"] = now
        query: dict[str, Any] = {"_id": task_id, "status": {"$in": allowed_from}}
        if status == TaskStatus.running:
            # keep the first start time when resuming after a hand-off
            existing = await self.db.tasks.find_one({"_id": task_id}, {"started_at": 1})
            if existing and existing.get("started_at"):
                update.pop("started_at", None)
        res = await self.db.tasks.update_one(query, {"$set": update})
        if res.modified_count:
            await self.add_event(task_id, EventType.status, status=status)
        return bool(res.modified_count)

    async def request_cancel(self, task_id: str) -> None:
        await self.db.tasks.update_one({"_id": task_id}, {"$set": {"cancel_requested": True}})

    async def is_cancel_requested(self, task_id: str) -> bool:
        doc = await self.db.tasks.find_one({"_id": task_id}, {"cancel_requested": 1, "status": 1})
        return doc is None or bool(doc.get("cancel_requested")) or doc.get("status") in TERMINAL

    async def delete_for_user(self, user_id: str) -> list[str]:
        ids = [d["_id"] async for d in self.db.tasks.find({"user_id": user_id}, {"_id": 1})]
        if ids:
            await self.db.tasks.delete_many({"_id": {"$in": ids}})
            await self.db.jobs.delete_many({"task_id": {"$in": ids}})
            await self.db.handoffs.delete_many({"task_id": {"$in": ids}})
        return ids


def public_task(doc: dict[str, Any], include_events: bool = True) -> dict[str, Any]:
    out = {
        "id": doc["_id"],
        "flow_id": doc["flow_id"],
        "flow_version": doc.get("flow_version"),
        "title": doc.get("title"),
        "params": doc.get("params", {}),
        "status": doc["status"],
        "result": doc.get("result"),
        "error": doc.get("error"),
        "created_at": doc["created_at"],
        "started_at": doc.get("started_at"),
        "finished_at": doc.get("finished_at"),
    }
    if include_events:
        out["events"] = doc.get("events", [])
    return out
