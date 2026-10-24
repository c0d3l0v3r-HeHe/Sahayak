import asyncio

import httpx
import pytest

from app.core.security import internal_token
from app.handoff.service import HandoffService
from app.models.common import LocalizedText
from app.worker.internal import create_internal_app


@pytest.mark.mongo
async def test_api_delivers_answer_to_remote_worker(db, monkeypatch):
    """API process -> worker's internal HTTP endpoint -> waiting coroutine."""
    internal = create_internal_app()
    svc = HandoffService(db)
    doc, fut = await svc.open(
        "task-remote", "captcha", LocalizedText(en="x", hi="x"), 30, "http://worker-1:8100"
    )
    waiter = asyncio.create_task(svc.wait(doc["_id"], fut, 30))

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.ASGITransport(app=internal)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.handoff.service.httpx.AsyncClient", fake_client)
    assert await svc.answer("task-remote", doc["_id"], "ABC12")
    assert await waiter == "ABC12"


async def test_internal_endpoint_requires_token():
    transport = httpx.ASGITransport(app=create_internal_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://w") as c:
        assert (await c.post("/internal/handoffs/x", json={"value": "a"})).status_code == 403
        ok = await c.post(
            "/internal/handoffs/x",
            json={"value": "a"},
            headers={"X-Internal-Token": internal_token()},
        )
        assert ok.json() == {"delivered": False}
