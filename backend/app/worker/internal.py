"""Tiny internal HTTP endpoint on each worker: receives hand-off answers from the API.

Answers arrive here and go straight to the waiting coroutine; they are never stored.
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.security import check_internal_token
from app.handoff.service import deliver_local


class Delivery(BaseModel):
    value: str | None = Field(default=None, max_length=200, repr=False)
    cancel: bool = False


def create_internal_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/internal/handoffs/{handoff_id}")
    async def deliver(
        handoff_id: str, body: Delivery, x_internal_token: str | None = Header(default=None)
    ) -> dict:
        if not check_internal_token(x_internal_token):
            raise HTTPException(status_code=403)
        return {"delivered": deliver_local(handoff_id, body.value, cancel=body.cancel)}

    @app.get("/internal/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
