import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse
from app.crud import notes as notes_crud

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(note_in: NoteCreate, db: AsyncSession = Depends(get_db)):
    return await notes_crud.create_note(db, note_in)


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    q: str | None = Query(default=None, description="Keyword search across title and content"),
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await notes_crud.get_notes(db, q=q, limit=limit, offset=offset)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    note = await notes_crud.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID, note_in: NoteUpdate, db: AsyncSession = Depends(get_db)
):
    note = await notes_crud.update_note(db, note_id, note_in)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await notes_crud.delete_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
