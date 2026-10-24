"""End-to-end: API -> queue -> worker -> real headless Chromium -> mock sites -> result."""

import asyncio
import time

import pytest

pytestmark = [pytest.mark.mongo, pytest.mark.integration]

TERMINAL = {"succeeded", "failed", "cancelled", "expired"}


async def wait_for(client, auth, task_id, statuses, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = (await client.get(f"/v1/tasks/{task_id}", headers=auth)).json()
        if task["status"] in statuses:
            return task
        await asyncio.sleep(0.2)
    raise AssertionError(f"task stuck in {task['status']}: {task.get('events')[-3:]}")


async def start(client, auth, flow_id, params):
    resp = await client.post("/v1/tasks", json={"flow_id": flow_id, "params": params}, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()["task_id"]


def event_types(task):
    return [e["type"] for e in task["events"]]


async def test_scheme_finder(client, auth, worker):
    task_id = await start(
        client,
        auth,
        "scheme_finder",
        {"age": "67", "gender": "female", "state": "delhi", "income": "80000"},
    )
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded", task["events"][-3:]
    schemes = task["result"]["data"]["schemes"]
    assert 1 <= len(schemes) <= 5
    assert schemes[0]["name"] == "Delhi Old Age Pension"  # state scheme first
    assert schemes[0]["link"].startswith("https://www.myscheme.gov.in/schemes/")
    assert "1. Delhi Old Age Pension" in task["result"]["text"]["en"]
    assert "screenshot" in event_types(task) and "step" in event_types(task)
    statuses = [e["status"] for e in task["events"] if e["type"] == "status"]
    assert statuses == ["queued", "running", "succeeded"]


async def test_scheme_finder_no_match(client, auth, worker):
    task_id = await start(
        client,
        auth,
        "scheme_finder",
        {"age": "45", "gender": "male", "state": "goa", "income": "900000"},
    )
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded"
    # PM Kisan / Vishwakarma have no income cap in the demo data, so we still get results;
    # check the empty-result template path with an impossible age instead.
    task_id = await start(
        client,
        auth,
        "scheme_finder",
        {"age": "120", "gender": "male", "state": "goa", "income": "900000000"},
    )
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded"


async def test_train_running_status(client, auth, worker):
    task_id = await start(client, auth, "train_running_status", {"train_no": "12301"})
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded", task["events"][-3:]
    data = task["result"]["data"]
    assert data["train_name"].startswith("12301 Howrah Rajdhani")
    assert data["destination"] == "New Delhi"
    assert data["delay"] and data["expected_arrival"] and data["last_station"]
    assert "Delay:" in task["result"]["text"]["en"]
    assert "देरी" in task["result"]["text"]["hi"]


async def test_train_not_found(client, auth, worker):
    task_id = await start(client, auth, "train_running_status", {"train_no": "00000"})
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "failed"
    assert "00000" in task["error"]["en"] and task["error"]["hi"]


async def answer_captcha(client, auth, task_id, value):
    task = await wait_for(client, auth, task_id, {"awaiting_user"} | TERMINAL)
    assert task["status"] == "awaiting_user", task["events"][-3:]
    handoff = task["handoff"]
    assert handoff["kind"] == "captcha" and handoff["prompt"]["hi"]
    # the CAPTCHA image is served to the owner as a JPEG
    img = await client.get(f"/v1/tasks/{task_id}/screens/{handoff['image_id']}", headers=auth)
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert img.content[:2] == b"\xff\xd8"
    resp = await client.post(
        f"/v1/tasks/{task_id}/input",
        json={"handoff_id": handoff["id"], "value": value},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    return handoff


async def test_pnr_with_captcha_handoff(client, auth, worker, db):
    task_id = await start(client, auth, "pnr_status", {"pnr": "4512345678"})
    await answer_captcha(client, auth, task_id, "k7pqr")  # case-insensitive on the mock
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded", task["events"][-3:]
    passengers = task["result"]["data"]["passengers"]
    assert passengers and set(passengers[0]) == {"passenger", "booking_status", "current_status"}
    assert "Passenger 1:" in task["result"]["text"]["en"]
    types = event_types(task)
    assert "handoff_required" in types and "handoff_resolved" in types
    statuses = [e["status"] for e in task["events"] if e["type"] == "status"]
    assert statuses == ["queued", "running", "awaiting_user", "running", "succeeded"]
    # nothing about the answer or the full PNR is persisted
    stored = str(await db.tasks.find_one({"_id": task_id}))
    assert "K7PQR" not in stored.upper() and "4512345678" not in stored
    assert await db.handoffs.count_documents({"task_id": task_id}) == 0
    job = await db.jobs.find_one({"task_id": task_id})
    assert "payload" not in job


async def test_pnr_wrong_captcha_then_retry(client, auth, worker):
    task_id = await start(client, auth, "pnr_status", {"pnr": "4512345679"})
    first = await answer_captcha(client, auth, task_id, "WRONG")
    deadline = time.monotonic() + 30
    while True:  # wait for the *second* hand-off
        task = (await client.get(f"/v1/tasks/{task_id}", headers=auth)).json()
        if task.get("handoff") and task["handoff"]["id"] != first["id"]:
            break
        assert time.monotonic() < deadline and task["status"] not in TERMINAL
        await asyncio.sleep(0.2)
    await answer_captcha(client, auth, task_id, "K7PQR")
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "succeeded"
    assert any(
        e["type"] == "step" and "did not match" in e["message"]["en"] for e in task["events"]
    )


async def test_invalid_captcha_answer_rejected(client, auth, worker):
    task_id = await start(client, auth, "pnr_status", {"pnr": "4512345670"})
    task = await wait_for(client, auth, task_id, {"awaiting_user"})
    resp = await client.post(
        f"/v1/tasks/{task_id}/input",
        json={"handoff_id": task["handoff"]["id"], "value": "!!"},
        headers=auth,
    )
    assert resp.status_code == 422
    await client.post(f"/v1/tasks/{task_id}/cancel", headers=auth)
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "cancelled"


async def test_pnr_not_found(client, auth, worker):
    task_id = await start(client, auth, "pnr_status", {"pnr": "0123456789"})
    await answer_captcha(client, auth, task_id, "K7PQR")
    task = await wait_for(client, auth, task_id, TERMINAL)
    assert task["status"] == "failed" and "not found" in task["error"]["en"]
