from fastapi import APIRouter, Depends

from app.api.deps import AppState, get_state

router = APIRouter(tags=["flows"])


@router.get("/flows")
async def list_flows(state: AppState = Depends(get_state)) -> dict:
    return {"flows": [f.public() for f in state.registry.all()]}
