import asyncio
from datetime import timedelta

import pytest

from app.handoff.service import (
    LOCAL,
    HandoffCancelled,
    HandoffService,
    HandoffTimeout,
    InvalidAnswer,
    normalize_answer,
)
from app.models.common import LocalizedText, utcnow

PROMPT = LocalizedText(en="Read the letters", hi="अक्षर पढ़िए")


def test_normalize_answers():
    assert normalize_answer("captcha", " k7 pqr ") == "k7pqr"
    assert normalize_answer("otp", "48 29 13") == "482913"
    assert normalize_answer("confirm", "हाँ") == "yes"
    assert normalize_answer("confirm", "Nahi") == "no"
    for kind, bad in [("captcha", "a$b"), ("otp", "12"), ("confirm", "maybe"), ("param", " ")]:
        with pytest.raises(InvalidAnswer):
            normalize_answer(kind, bad)


@pytest.mark.mongo
async def test_ttl_indexes_exist(db):
    for col, name in [(db.handoffs, "handoffs_ttl"), (db.tasks, "tasks_ttl")]:
        info = await col.index_information()
        assert info[name]["expireAfterSeconds"] == 0
        assert info[name]["key"] == [("expires_at", 1)]


@pytest.mark.mongo
async def test_handoff_expires_within_ten_minutes(db):
    svc = HandoffService(db, ttl_minutes=10)
    doc, fut = await svc.open("task-a", "captcha", PROMPT, 3600, LOCAL)
    assert doc["expires_at"] - utcnow() <= timedelta(minutes=10)
    fut.cancel()
    await db.handoffs.delete_one({"_id": doc["_id"]})


@pytest.mark.mongo
async def test_answer_reaches_worker_and_is_not_persisted(db):
    svc = HandoffService(db)
    doc, fut = await svc.open("task-b", "captcha", PROMPT, 30, LOCAL)
    waiter = asyncio.create_task(svc.wait(doc["_id"], fut, 30))
    await asyncio.sleep(0.05)
    assert await svc.answer("task-b", doc["_id"], "K7PQR")
    assert await waiter == "K7PQR"
    # the record is gone and no field anywhere ever held the answer
    assert await db.handoffs.find_one({"_id": doc["_id"]}) is None
    async for other in db.handoffs.find({}):
        assert "K7PQR" not in str(other)


@pytest.mark.mongo
async def test_answer_for_wrong_task_rejected(db):
    svc = HandoffService(db)
    doc, fut = await svc.open("task-c", "otp", PROMPT, 30, LOCAL)
    assert not await svc.answer("other-task", doc["_id"], "123456")
    fut.cancel()
    await db.handoffs.delete_one({"_id": doc["_id"]})


@pytest.mark.mongo
async def test_timeout(db):
    svc = HandoffService(db)
    doc, fut = await svc.open("task-d", "otp", PROMPT, 0.1, LOCAL)
    with pytest.raises(HandoffTimeout):
        await svc.wait(doc["_id"], fut, 0.1)
    assert await db.handoffs.find_one({"_id": doc["_id"]}) is None


@pytest.mark.mongo
async def test_cancel(db):
    svc = HandoffService(db)
    doc, fut = await svc.open("task-e", "confirm", PROMPT, 30, LOCAL)
    waiter = asyncio.create_task(svc.wait(doc["_id"], fut, 30))
    await asyncio.sleep(0.05)
    await svc.cancel_for_task("task-e")
    with pytest.raises(HandoffCancelled):
        await waiter
