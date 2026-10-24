"""Hand-offs: moments where a human must act (CAPTCHA, OTP, confirmation, missing detail).

The hand-off *record* (kind, prompt, image) lives in Mongo with a 10-minute TTL so the app can
render it. The *answer* is never written anywhere: the API forwards it straight to the waiting
worker — in-process when the worker is embedded, otherwise over the worker's internal HTTP port.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx

from app.core.security import internal_token
from app.db.mongo import Database
from app.models.common import LocalizedText, new_id, utcnow

log = logging.getLogger(__name__)

LOCAL = "local"


class HandoffTimeout(Exception):
    pass


class HandoffCancelled(Exception):
    pass


class InvalidAnswer(ValueError):
    pass


@dataclass
class _Cancel:
    pass


# Process-local registry of workers waiting for an answer: handoff_id -> future.
_pending: dict[str, asyncio.Future[Any]] = {}


def deliver_local(handoff_id: str, value: str | None, cancel: bool = False) -> bool:
    fut = _pending.get(handoff_id)
    if fut is None or fut.done():
        return False
    fut.set_result(_Cancel() if cancel else value)
    return True


YES = {"yes", "y", "haan", "han", "ha", "haa", "हाँ", "हां", "हा", "true", "1", "ok", "theek hai"}
NO = {"no", "n", "nahi", "nahin", "नहीं", "नही", "false", "0"}


def normalize_answer(kind: str, value: str) -> str:
    v = value.strip()
    if kind == "captcha":
        v = re.sub(r"\s+", "", v)
        if not re.fullmatch(r"[A-Za-z0-9]{1,12}", v):
            raise InvalidAnswer("captcha")
    elif kind == "otp":
        v = re.sub(r"\D", "", v)
        if not re.fullmatch(r"\d{4,8}", v):
            raise InvalidAnswer("otp")
    elif kind == "confirm":
        low = v.lower()
        if low in YES:
            v = "yes"
        elif low in NO:
            v = "no"
        else:
            raise InvalidAnswer("confirm")
    elif not v:
        raise InvalidAnswer(kind)
    return v


class HandoffService:
    def __init__(self, db: Database, ttl_minutes: int = 10):
        self.db = db
        self.ttl = timedelta(minutes=ttl_minutes)

    # ---- worker side -------------------------------------------------------

    async def open(
        self,
        task_id: str,
        kind: str,
        prompt: LocalizedText,
        timeout_s: float,
        worker_url: str,
        image_id: str | None = None,
        param: str | None = None,
    ) -> tuple[dict[str, Any], asyncio.Future[Any]]:
        """Create a hand-off record and register a waiter. Returns (record, future)."""
        handoff_id = new_id()
        now = utcnow()
        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        _pending[handoff_id] = fut
        doc = {
            "_id": handoff_id,
            "task_id": task_id,
            "kind": kind,
            "prompt": prompt.model_dump(),
            "image_id": image_id,
            "param": param,
            "worker_url": worker_url,
            "created_at": now,
            "expires_at": now + min(self.ttl, timedelta(seconds=timeout_s + 60)),
        }
        await self.db.handoffs.insert_one(doc)
        return doc, fut

    async def wait(self, handoff_id: str, fut: asyncio.Future[Any], timeout_s: float) -> str:
        return await self._wait(handoff_id, fut, timeout_s)

    async def _wait(self, handoff_id: str, fut: asyncio.Future[Any], timeout_s: float) -> str:
        try:
            value = await asyncio.wait_for(fut, timeout=timeout_s)
        except TimeoutError as exc:
            raise HandoffTimeout() from exc
        finally:
            _pending.pop(handoff_id, None)
            await self.db.handoffs.delete_one({"_id": handoff_id})
        if isinstance(value, _Cancel):
            raise HandoffCancelled()
        return value

    # ---- API side ----------------------------------------------------------

    async def pending_for_task(self, task_id: str) -> dict[str, Any] | None:
        return await self.db.handoffs.find_one(
            {"task_id": task_id, "expires_at": {"$gt": utcnow()}}, sort=[("created_at", -1)]
        )

    async def answer(self, task_id: str, handoff_id: str, value: str) -> bool:
        doc = await self.db.handoffs.find_one({"_id": handoff_id, "task_id": task_id})
        if doc is None or doc["expires_at"] <= utcnow():
            return False
        clean = normalize_answer(doc["kind"], value)
        return await self._deliver(doc, clean, cancel=False)

    async def cancel_for_task(self, task_id: str) -> None:
        async for doc in self.db.handoffs.find({"task_id": task_id}):
            await self._deliver(doc, None, cancel=True)

    async def _deliver(self, doc: dict[str, Any], value: str | None, cancel: bool) -> bool:
        url = doc.get("worker_url") or LOCAL
        if url == LOCAL:
            return deliver_local(doc["_id"], value, cancel)
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{url}/internal/handoffs/{doc['_id']}",
                    headers={"X-Internal-Token": internal_token()},
                    json={"value": value, "cancel": cancel},
                )
            return resp.status_code == 200 and resp.json().get("delivered", False)
        except httpx.HTTPError:
            log.warning("could not reach worker for hand-off %s", doc["_id"])
            return False
