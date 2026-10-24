"""Durable, anonymous counters per flow (survive the 7-day task TTL; no personal data).

One document per flow: {_id: flow_id, by_status: {...}, duration_sum_s, buckets: {...},
minutes_saved}. Feeds the public /v1/stats demo counters and Prometheus /metrics.
"""

from datetime import datetime
from typing import Any

from app.db.mongo import Database
from app.flows.registry import FlowRegistry
from app.models.common import utcnow
from app.models.flow import FlowDefinition
from app.models.task import TaskStatus

# Upper bounds (seconds) for the task-duration histogram.
BUCKETS = (5, 10, 30, 60, 120, 300, 600)


def bucket_key(seconds: float) -> str:
    for b in BUCKETS:
        if seconds <= b:
            return f"le_{b}"
    return "le_inf"


class StatsService:
    def __init__(self, db: Database):
        self.col = db.db["stats"]

    async def record(
        self, flow: FlowDefinition, status: TaskStatus, started_at: datetime | None
    ) -> None:
        inc: dict[str, Any] = {f"by_status.{status.value}": 1}
        if status == TaskStatus.succeeded:
            inc["minutes_saved"] = flow.est_minutes_saved
            if started_at is not None:
                duration = max(0.0, (utcnow() - started_at).total_seconds())
                inc["duration_sum_s"] = duration
                inc["duration_count"] = 1
                inc[f"buckets.{bucket_key(duration)}"] = 1
        await self.col.update_one({"_id": flow.id}, {"$inc": inc}, upsert=True)

    async def all(self) -> list[dict[str, Any]]:
        return [doc async for doc in self.col.find({})]

    async def summary(self, registry: FlowRegistry) -> dict[str, Any]:
        docs = {d["_id"]: d for d in await self.all()}
        by_flow = []
        totals = {"succeeded": 0, "finished": 0, "duration_sum": 0.0, "duration_n": 0, "saved": 0.0}
        for flow in registry.all(enabled_only=False):
            d = docs.get(flow.id, {})
            st = d.get("by_status", {})
            succeeded = int(st.get("succeeded", 0))
            finished = sum(int(v) for v in st.values())
            totals["succeeded"] += succeeded
            totals["finished"] += finished
            totals["duration_sum"] += float(d.get("duration_sum_s", 0))
            totals["duration_n"] += int(d.get("duration_count", 0))
            totals["saved"] += float(d.get("minutes_saved", 0))
            by_flow.append(
                {
                    "flow_id": flow.id,
                    "title": flow.title.model_dump(),
                    "succeeded": succeeded,
                    "finished": finished,
                    "minutes_saved": round(float(d.get("minutes_saved", 0)), 1),
                }
            )
        n = totals["duration_n"]
        return {
            "tasks_completed": totals["succeeded"],
            "tasks_finished": totals["finished"],
            "success_rate": round(totals["succeeded"] / totals["finished"], 3)
            if totals["finished"]
            else None,
            "average_duration_s": round(totals["duration_sum"] / n, 1) if n else None,
            "minutes_saved": round(totals["saved"], 1),
            "by_flow": by_flow,
        }
