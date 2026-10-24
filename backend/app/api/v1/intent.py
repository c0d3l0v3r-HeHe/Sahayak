from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import AppState, current_user, get_state
from app.intent.service import IntentService

router = APIRouter(tags=["intent"])


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: Literal["hi", "en"] = "hi"
    # Optional conversation context for one-question-at-a-time follow-ups:
    flow_id: str | None = None
    params: dict[str, str] | None = None
    expecting: str | None = None  # name of the param the app just asked for


def get_intent_service(request: Request, state: AppState = Depends(get_state)) -> IntentService:
    service = getattr(request.app.state, "intent", None)
    if service is None:
        service = IntentService(state.settings, state.registry)
        request.app.state.intent = service
    return service


@router.post("/intent/parse")
async def parse_intent(
    body: ParseRequest,
    _user: dict = Depends(current_user),
    service: IntentService = Depends(get_intent_service),
) -> dict:
    return await service.parse(body.text, body.lang, body.flow_id, body.params, body.expecting)
