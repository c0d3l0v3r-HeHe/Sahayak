from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.security import AuthError, decode_token
from app.db.mongo import Database
from app.flows.registry import FlowRegistry
from app.handoff.service import HandoffService
from app.queue.base import JobQueue
from app.services.screens import ScreenStore
from app.services.tasks import TaskService


@dataclass
class AppState:
    settings: Settings
    db: Database
    registry: FlowRegistry
    tasks: TaskService
    handoffs: HandoffService
    queue: JobQueue
    screens: ScreenStore


def get_state(request: Request) -> AppState:
    return request.app.state.sahayak


_bearer = HTTPBearer(auto_error=False)


async def user_from_token(state: AppState, token: str | None) -> dict:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        user_id = decode_token(token)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
    user = await state.db.users.find_one({"_id": user_id})
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return user


async def current_user(
    state: AppState = Depends(get_state),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    return await user_from_token(state, creds.credentials if creds else None)
