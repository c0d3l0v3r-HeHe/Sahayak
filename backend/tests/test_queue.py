import asyncio
from datetime import timedelta

import pytest

from app.models.common import utcnow
from app.queue.mongo_queue import MongoJobQueue

pytestmark = pytest.mark.mongo


@pytest.fixture
async def queue(db):
    await db.jobs.delete_many({})
    return MongoJobQueue(db, claim_timeout_s=60, max_attempts=2)


async def test_enqueue_and_claim(queue):
    await queue.enqueue("t1", {"params": {"pnr": "4512345678"}})
    job = await queue.claim("w1")
    assert job is not None and job.task_id == "t1" and job.attempts == 1
    assert job.payload == {"params": {"pnr": "4512345678"}}
    assert await queue.claim("w2") is None


async def test_concurrent_claims_are_exclusive(queue):
    for i in range(5):
        await queue.enqueue(f"t{i}")
    jobs = await asyncio.gather(*(queue.claim(f"w{i}") for i in range(20)))
    claimed = [j.task_id for j in jobs if j]
    assert sorted(claimed) == [f"t{i}" for i in range(5)]


async def test_run_after_delays_job(queue):
    await queue.enqueue("later", delay_s=60)
    assert await queue.claim("w1") is None
    assert await queue.depth() == 1


async def test_complete_removes_payload(queue, db):
    job_id = await queue.enqueue("t1", {"params": {"pnr": "4512345678"}})
    job = await queue.claim("w1")
    await queue.complete(job.id, "w1")
    doc = await db.jobs.find_one({"_id": job_id})
    assert doc["state"] == "done" and "payload" not in doc


async def test_stale_claim_is_requeued(queue, db):
    job_id = await queue.enqueue("t1")
    await queue.claim("crashed-worker")
    await db.jobs.update_one(
        {"_id": job_id}, {"$set": {"claimed_at": utcnow() - timedelta(minutes=5)}}
    )
    job = await queue.claim("w2")
    assert job is not None and job.id == job_id and job.attempts == 2


async def test_heartbeat_keeps_claim(queue, db):
    job_id = await queue.enqueue("t1")
    await queue.claim("w1")
    await db.jobs.update_one(
        {"_id": job_id}, {"$set": {"claimed_at": utcnow() - timedelta(minutes=5)}}
    )
    assert await queue.heartbeat(job_id, "w1")
    assert await queue.claim("w2") is None
    assert not await queue.heartbeat(job_id, "someone-else")


async def test_exhausted_jobs(queue, db):
    job_id = await queue.enqueue("t1")
    await db.jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "state": "claimed",
                "attempts": 2,
                "claimed_at": utcnow() - timedelta(minutes=5),
            }
        },
    )
    assert await queue.claim("w1") is None
    assert await queue.exhausted() == ["t1"]
    assert (await db.jobs.find_one({"_id": job_id}))["state"] == "failed"


async def test_retry_later(queue):
    await queue.enqueue("t1")
    job = await queue.claim("w1")
    await queue.fail(job.id, "w1", retry_in_s=60)
    assert await queue.claim("w1") is None
