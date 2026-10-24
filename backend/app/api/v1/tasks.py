import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import AppState, current_user, get_state, user_from_token
from app.flows.validator import redacted_params, validate_params
from app.handoff.service import InvalidAnswer
from app.models.task import TERMINAL, HandoffAnswer, TaskStatus
from app.services.tasks import public_task

router = APIRouter(tags=["tasks"])


class CreateTask(BaseModel):
    flow_id: str
    params: dict[str, str] = Field(default_factory=dict)
    lang: Literal["hi", "en"] | None = None


async def _own_task(state: AppState, task_id: str, user: dict) -> dict:
    task = await state.tasks.get(task_id)
    if task is None or task["user_id"] != user["_id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return task


async def _with_handoff(state: AppState, task: dict) -> dict:
    out = public_task(task)
    out["handoff"] = None
    if task["status"] == TaskStatus.awaiting_user.value:
        h = await state.handoffs.pending_for_task(task["_id"])
        if h:
            out["handoff"] = {
                "id": h["_id"],
                "kind": h["kind"],
                "prompt": h["prompt"],
                "image_id": h.get("image_id"),
                "param": h.get("param"),
                "expires_at": h["expires_at"],
            }
    return out


@router.post("/tasks", status_code=201)
async def create_task(
    body: CreateTask, user: dict = Depends(current_user), state: AppState = Depends(get_state)
) -> dict:
    flow = state.registry.get(body.flow_id)
    if flow is None or not flow.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown flow")
    clean, missing, invalid = validate_params(flow, body.params)
    if missing or invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"message": "invalid params", "missing": missing, "invalid": invalid},
        )
    lang = body.lang or user.get("language", "hi")
    task_id = await state.tasks.create(user["_id"], flow, redacted_params(flow, clean), lang)
    await state.queue.enqueue(task_id, {"params": clean})
    return {"task_id": task_id}


@router.get("/tasks")
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(current_user),
    state: AppState = Depends(get_state),
) -> dict:
    docs = await state.tasks.list_for_user(user["_id"], limit + 1, offset)
    return {
        "tasks": [public_task(d, include_events=False) for d in docs[:limit]],
        "next_offset": offset + limit if len(docs) > limit else None,
    }


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str, user: dict = Depends(current_user), state: AppState = Depends(get_state)
) -> dict:
    return await _with_handoff(state, await _own_task(state, task_id, user))


@router.post("/tasks/{task_id}/input")
async def answer_handoff(
    task_id: str,
    body: HandoffAnswer,
    user: dict = Depends(current_user),
    state: AppState = Depends(get_state),
) -> dict:
    task = await _own_task(state, task_id, user)
    if task["status"] != TaskStatus.awaiting_user.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "task is not waiting for input")
    try:
        delivered = await state.handoffs.answer(task_id, body.handoff_id, body.value)
    except InvalidAnswer as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"invalid {exc}") from None
    if not delivered:
        raise HTTPException(status.HTTP_410_GONE, "hand-off expired")
    return {"accepted": True}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str, user: dict = Depends(current_user), state: AppState = Depends(get_state)
) -> dict:
    task = await _own_task(state, task_id, user)
    if TaskStatus(task["status"]) in TERMINAL:
        raise HTTPException(status.HTTP_409_CONFLICT, "task already finished")
    await state.tasks.request_cancel(task_id)
    if task["status"] == TaskStatus.queued.value:
        await state.tasks.set_status(task_id, TaskStatus.cancelled)
    await state.handoffs.cancel_for_task(task_id)
    return {"cancelled": True}


@router.get("/tasks/{task_id}/screens/{screenshot_id}")
async def get_screen(
    task_id: str,
    screenshot_id: str,
    user: dict = Depends(current_user),
    state: AppState = Depends(get_state),
) -> FileResponse:
    await _own_task(state, task_id, user)
    path = state.screens.path(task_id, screenshot_id)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "screenshot not found")
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"}
    )


@router.websocket("/tasks/{task_id}/events")
async def task_events(websocket: WebSocket, task_id: str, token: str | None = None) -> None:
    """Streams task events. Clients may resume with `?after=<seq>`."""
    state: AppState = websocket.app.state.sahayak
    auth = websocket.headers.get("authorization", "")
    token = token or (auth[7:] if auth.lower().startswith("bearer ") else None)
    try:
        user = await user_from_token(state, token)
        task = await _own_task(state, task_id, user)
    except HTTPException:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    last = int(websocket.query_params.get("after", 0) or 0)
    try:
        while True:
            for event in task.get("events", []):
                if event["seq"] > last:
                    await websocket.send_json(jsonable_encoder(event))
                    last = event["seq"]
            if TaskStatus(task["status"]) in TERMINAL:
                await websocket.close(code=1000)
                return
            await asyncio.sleep(0.3)
            latest = await state.tasks.get(task_id)
            if latest is None:
                await websocket.close(code=1000)
                return
            task = latest
    except WebSocketDisconnect:
        return
