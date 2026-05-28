from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.note import AskRequest, AskResponse, NoteResponse
from app.crud import notes as notes_crud
from app.llm import generate_answer

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask_question(req: AskRequest, db: AsyncSession = Depends(get_db)):
    results = await notes_crud.search_notes_semantic(db, req.q, req.limit)
    answer = await generate_answer(req.q, results)
    sources = [NoteResponse.model_validate(note) for note, _ in results]
    return AskResponse(answer=answer, sources=sources)
