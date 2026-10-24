from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from app.api.deps import AppState, current_user, get_state
from app.core.security import create_token
from app.models.common import new_id, utcnow

router = APIRouter(tags=["auth"])


class AnonymousLogin(BaseModel):
    device_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    language: Literal["hi", "en"] | None = None


class MeUpdate(BaseModel):
    language: Literal["hi", "en"]


@router.post("/auth/anonymous")
async def anonymous(body: AnonymousLogin, state: AppState = Depends(get_state)) -> dict:
    now = utcnow()
    update: dict = {
        "$set": {"last_seen_at": now},
        "$setOnInsert": {"_id": new_id(), "created_at": now},
    }
    if body.language:
        update["$set"]["language"] = body.language
    else:
        update["$setOnInsert"]["language"] = "hi"
    user = await state.db.users.find_one_and_update(
        {"device_id": body.device_id}, update, upsert=True, return_document=ReturnDocument.AFTER
    )
    assert user is not None  # upsert always returns a document
    return {
        "token": create_token(user["_id"]),
        "user_id": user["_id"],
        "language": user["language"],
    }


@router.get("/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"user_id": user["_id"], "language": user.get("language", "hi")}


@router.patch("/me")
async def update_me(
    body: MeUpdate, user: dict = Depends(current_user), state: AppState = Depends(get_state)
) -> dict:
    await state.db.users.update_one({"_id": user["_id"]}, {"$set": {"language": body.language}})
    return {"user_id": user["_id"], "language": body.language}


@router.delete("/me")
async def delete_me(
    user: dict = Depends(current_user), state: AppState = Depends(get_state)
) -> dict:
    """'Delete my data': removes the user, their tasks, jobs, hand-offs and screenshots."""
    for task_id in await state.tasks.delete_for_user(user["_id"]):
        state.screens.delete_task(task_id)
    await state.db.users.delete_one({"_id": user["_id"]})
    return {"deleted": True}
