from fastapi import APIRouter
from app.schemas.note import DraftRequest, DraftResponse
from app.agent import draft_note

router = APIRouter(prefix="/draft", tags=["draft"])


@router.post("", response_model=DraftResponse)
async def draft_note_endpoint(request: DraftRequest) -> DraftResponse:
    note = await draft_note(request.content)
    return DraftResponse(draft=note)
