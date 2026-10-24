from datetime import timedelta

import pytest

from app.flows.registry import get_registry
from app.models.common import utcnow
from app.models.task import TaskStatus
from app.services.stats import StatsService, bucket_key

pytestmark = pytest.mark.mongo


def test_bucket_key():
    assert bucket_key(3) == "le_5"
    assert bucket_key(45) == "le_60"
    assert bucket_key(10_000) == "le_inf"


async def test_stats_and_metrics(client, db):
    svc = StatsService(db)
    flow = get_registry().get("pnr_status")
    before = await svc.summary(get_registry())
    await svc.record(flow, TaskStatus.succeeded, utcnow() - timedelta(seconds=40))
    await svc.record(flow, TaskStatus.failed, utcnow())

    body = (await client.get("/v1/stats")).json()
    assert body["tasks_completed"] == before["tasks_completed"] + 1
    assert body["tasks_finished"] == before["tasks_finished"] + 2
    assert 0 < body["success_rate"] <= 1
    assert body["minutes_saved"] >= flow.est_minutes_saved
    assert body["average_duration_s"] > 0
    assert {f["flow_id"] for f in body["by_flow"]} >= {"pnr_status", "scheme_finder"}

    resp = await client.get("/metrics")
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/plain")
    text = resp.text
    assert "sahayak_queue_depth" in text
    assert 'sahayak_tasks_total{flow="pnr_status",status="succeeded"}' in text
    assert 'sahayak_task_duration_seconds_bucket{flow="pnr_status",le="60.0"}' in text
    assert "sahayak_tasks_active" in text


async def test_worker_records_finished_tasks(client, auth, worker, db):
    """End to end: a finished task bumps the durable counters."""
    import asyncio

    before = (await client.get("/v1/stats")).json()
    resp = await client.post(
        "/v1/tasks",
        json={"flow_id": "train_running_status", "params": {"train_no": "12951"}},
        headers=auth,
    )
    task_id = resp.json()["task_id"]
    for _ in range(200):
        task = (await client.get(f"/v1/tasks/{task_id}", headers=auth)).json()
        if task["status"] in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.2)
    await asyncio.sleep(0.3)
    after = (await client.get("/v1/stats")).json()
    assert after["tasks_finished"] == before["tasks_finished"] + 1
