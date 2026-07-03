import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.note import NoteUpdate, NoteResponse, PendingNoteResponse
from app.crud import pending as pending_crud

# Endpoints backing the web-UI "Pending" tab: list / edit / approve / reject the notes staged by
# the MCP create_note tool. There is deliberately no POST create here — staging happens only via
# the MCP server calling crud.create_pending directly (stdio), never over HTTP.
router = APIRouter(prefix="/pending", tags=["pending"])


@router.get("", response_model=list[PendingNoteResponse])
async def list_pending(
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await pending_crud.list_pending(db, limit=limit, offset=offset)


@router.put("/{pending_id}", response_model=PendingNoteResponse)
async def update_pending(
    pending_id: uuid.UUID, note_in: NoteUpdate, db: AsyncSession = Depends(get_db)
):
    pending = await pending_crud.update_pending(db, pending_id, note_in)
    if pending is None:
        raise HTTPException(status_code=404, detail="Pending note not found")
    return pending


@router.post("/{pending_id}/approve", response_model=NoteResponse, status_code=201)
async def approve_pending(pending_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Promotes into `notes` (embedding the final text) and deletes the pending row; returns the
    # new note, identical in shape to one created any other way.
    note = await pending_crud.approve_pending(db, pending_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Pending note not found")
    return note


@router.delete("/{pending_id}", status_code=204)
async def reject_pending(pending_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rejected = await pending_crud.reject_pending(db, pending_id)
    if not rejected:
        raise HTTPException(status_code=404, detail="Pending note not found")
