from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.note import QueryRequest, QueryResult, NoteResponse
from app.crud import notes as notes_crud

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=list[QueryResult])
async def semantic_query(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    results = await notes_crud.search_notes_semantic(db, req.q, req.limit)
    return [
        QueryResult(**NoteResponse.model_validate(note).model_dump(), score=score)
        for note, score in results
    ]
