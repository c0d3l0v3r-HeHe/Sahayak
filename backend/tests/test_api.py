import pytest
from fastapi.testclient import TestClient

from tests.conftest import login

pytestmark = pytest.mark.mongo


async def test_anonymous_login_is_idempotent(client):
    a = await client.post("/v1/auth/anonymous", json={"device_id": "device-123456"})
    b = await client.post("/v1/auth/anonymous", json={"device_id": "device-123456"})
    assert a.json()["user_id"] == b.json()["user_id"]


async def test_login_rejects_bad_device_id(client):
    assert (await client.post("/v1/auth/anonymous", json={"device_id": "x"})).status_code == 422


async def test_auth_required(client):
    assert (await client.get("/v1/tasks")).status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert (await client.get("/v1/tasks", headers=bad)).status_code == 401


async def test_list_flows(client):
    body = (await client.get("/v1/flows")).json()
    assert body["demo_mode"] is True
    flows = body["flows"]
    ids = {f["id"] for f in flows}
    assert ids == {"scheme_finder", "train_running_status", "pnr_status"}
    pnr = next(f for f in flows if f["id"] == "pnr_status")
    assert pnr["title"]["hi"] and pnr["params"][0]["prompt"]["hi"]
    assert "steps" not in pnr


async def test_create_task_validates_params(client, auth):
    resp = await client.post(
        "/v1/tasks", json={"flow_id": "pnr_status", "params": {}}, headers=auth
    )
    assert resp.status_code == 422 and resp.json()["detail"]["missing"] == ["pnr"]
    resp = await client.post(
        "/v1/tasks", json={"flow_id": "pnr_status", "params": {"pnr": "12"}}, headers=auth
    )
    assert resp.json()["detail"]["invalid"] == ["pnr"]
    resp = await client.post("/v1/tasks", json={"flow_id": "nope"}, headers=auth)
    assert resp.status_code == 404


async def test_task_lifecycle_without_worker(client, auth, db):
    resp = await client.post(
        "/v1/tasks", json={"flow_id": "pnr_status", "params": {"pnr": "4512345678"}}, headers=auth
    )
    assert resp.status_code == 201
    task_id = resp.json()["task_id"]
    task = (await client.get(f"/v1/tasks/{task_id}", headers=auth)).json()
    assert task["status"] == "queued"
    assert task["params"] == {"pnr": "••••••5678"}  # display copy is redacted
    stored = await db.tasks.find_one({"_id": task_id})
    assert "4512345678" not in str(stored)

    listing = (await client.get("/v1/tasks", headers=auth)).json()
    assert listing["tasks"][0]["id"] == task_id

    other = await login(client)
    assert (await client.get(f"/v1/tasks/{task_id}", headers=other)).status_code == 404

    assert (await client.post(f"/v1/tasks/{task_id}/cancel", headers=auth)).status_code == 200
    task = (await client.get(f"/v1/tasks/{task_id}", headers=auth)).json()
    assert task["status"] == "cancelled"
    assert (await client.post(f"/v1/tasks/{task_id}/cancel", headers=auth)).status_code == 409
    await db.jobs.delete_many({"task_id": task_id})


async def test_input_requires_waiting_task(client, auth):
    resp = await client.post(
        "/v1/tasks", json={"flow_id": "pnr_status", "params": {"pnr": "4512345678"}}, headers=auth
    )
    task_id = resp.json()["task_id"]
    resp = await client.post(
        f"/v1/tasks/{task_id}/input", json={"handoff_id": "x", "value": "y"}, headers=auth
    )
    assert resp.status_code == 409
    await client.post(f"/v1/tasks/{task_id}/cancel", headers=auth)


async def test_delete_my_data(client, db):
    headers = await login(client)
    resp = await client.post(
        "/v1/tasks",
        json={"flow_id": "pnr_status", "params": {"pnr": "4512345678"}},
        headers=headers,
    )
    task_id = resp.json()["task_id"]
    assert (await client.delete("/v1/me", headers=headers)).json() == {"deleted": True}
    assert await db.tasks.find_one({"_id": task_id}) is None
    assert await db.jobs.find_one({"task_id": task_id}) is None
    assert (await client.get("/v1/tasks", headers=headers)).status_code == 401


def test_websocket_streams_events(settings):
    from app.main import create_app

    with TestClient(create_app(settings)) as tc:
        token = tc.post("/v1/auth/anonymous", json={"device_id": "ws-device-1"}).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        task_id = tc.post(
            "/v1/tasks",
            json={"flow_id": "pnr_status", "params": {"pnr": "4512345678"}},
            headers=headers,
        ).json()["task_id"]
        tc.post(f"/v1/tasks/{task_id}/cancel", headers=headers)
        with tc.websocket_connect(f"/v1/tasks/{task_id}/events?token={token}") as ws:
            first = ws.receive_json()
            second = ws.receive_json()
        assert first["type"] == "status" and first["status"] == "queued"
        assert second["status"] == "cancelled"


def test_websocket_rejects_bad_token(settings):
    from starlette.websockets import WebSocketDisconnect

    from app.main import create_app

    with TestClient(create_app(settings)) as tc:
        with pytest.raises(WebSocketDisconnect):
            with tc.websocket_connect("/v1/tasks/abc/events?token=bad") as ws:
                ws.receive_json()
