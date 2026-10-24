"""Public demo counters and Prometheus metrics. Both are computed from Mongo at request time,
so they are correct no matter how many API and worker processes are running."""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
)
from prometheus_client.registry import Collector

from app.api.deps import AppState, get_state
from app.services.stats import BUCKETS, StatsService

router = APIRouter(tags=["stats"])
metrics_router = APIRouter(tags=["stats"])


@router.get("/stats")
async def stats(state: AppState = Depends(get_state)) -> dict:
    return await StatsService(state.db).summary(state.registry)


class _Snapshot(Collector):
    def __init__(self, depth: int, active: dict[str, int], docs: list[dict[str, Any]]):
        self.depth, self.active, self.docs = depth, active, docs

    def collect(self):  # type: ignore[override]
        yield GaugeMetricFamily("sahayak_queue_depth", "Jobs waiting to run", value=self.depth)
        active = GaugeMetricFamily(
            "sahayak_tasks_active", "Unfinished tasks by status", labels=["status"]
        )
        for status, n in sorted(self.active.items()):
            active.add_metric([status], n)
        yield active
        totals = CounterMetricFamily(
            "sahayak_tasks", "Finished tasks by flow and outcome", labels=["flow", "status"]
        )
        hist = HistogramMetricFamily(
            "sahayak_task_duration_seconds", "Duration of successful tasks", labels=["flow"]
        )
        for d in self.docs:
            for status, n in sorted(d.get("by_status", {}).items()):
                totals.add_metric([d["_id"], status], n)
            buckets = d.get("buckets", {})
            cumulative, rows = 0, []
            for b in BUCKETS:
                cumulative += int(buckets.get(f"le_{b}", 0))
                rows.append((str(float(b)), cumulative))
            cumulative += int(buckets.get("le_inf", 0))
            rows.append(("+Inf", cumulative))
            hist.add_metric([d["_id"]], rows, sum_value=float(d.get("duration_sum_s", 0)))
        yield totals
        yield hist


@metrics_router.get("/metrics")
async def metrics(state: AppState = Depends(get_state)) -> Response:
    depth = await state.queue.depth()
    active: dict[str, int] = {}
    async for row in await state.db.tasks.aggregate(
        [
            {"$match": {"status": {"$in": ["queued", "running", "awaiting_user"]}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}}},
        ]
    ):
        active[row["_id"]] = row["n"]
    registry = CollectorRegistry(auto_describe=False)
    registry.register(_Snapshot(depth, active, await StatsService(state.db).all()))
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
