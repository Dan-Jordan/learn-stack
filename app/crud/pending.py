"""CRUD for staged (pending) notes captured via the MCP create_note tool.

A pending note lives in its own `pending_notes` table until a human reviews it in the web-UI
"Pending" tab. Approval promotes it into `notes` by calling the *existing* crud.notes.create_note
(which embeds the final text), then deletes the pending row — so an approved note is byte-for-byte
the same shape as one created any other way. This module imports from crud.notes one-way; notes.py
knows nothing about pending, so there's no cycle.
"""

import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note, PendingNote
from app.schemas.note import NoteCreate, NoteUpdate
from app.crud.notes import create_note

logger = logging.getLogger(__name__)


async def create_pending(db: AsyncSession, note_in: NoteCreate) -> PendingNote:
    """Stage a note for review. Deliberately does not embed — embedding happens only at approval."""
    pending = PendingNote(**note_in.model_dump())
    db.add(pending)
    await db.commit()
    await db.refresh(pending)
    logger.info("Staged pending note %s (type=%s)", pending.id, pending.note_type)
    return pending


async def get_pending(db: AsyncSession, pending_id: uuid.UUID) -> PendingNote | None:
    result = await db.execute(select(PendingNote).where(PendingNote.id == pending_id))
    return result.scalar_one_or_none()


async def list_pending(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> list[PendingNote]:
    stmt = (
        select(PendingNote)
        .order_by(PendingNote.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_pending(
    db: AsyncSession, pending_id: uuid.UUID, note_in: NoteUpdate
) -> PendingNote | None:
    """Edit a staged note in place. A cheap text UPDATE — no re-embed (pending notes have none)."""
    pending = await get_pending(db, pending_id)
    if pending is None:
        return None
    updates = note_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(pending, field, value)
    await db.commit()
    await db.refresh(pending)
    # Field names only, never the new values (mirrors update_note's logging discipline).
    logger.info("Updated pending note %s (fields=%s)", pending_id, sorted(updates))
    return pending


async def approve_pending(db: AsyncSession, pending_id: uuid.UUID) -> Note | None:
    """Promote a staged note into `notes`, then delete the pending row.

    Promote-then-delete order is deliberate: create_note embeds + inserts + commits first, so if
    the subsequent delete ever failed we'd keep the real note and a stale (rejectable) pending row
    rather than risk losing the note. This spans two commits — acceptable at personal scale.
    """
    pending = await get_pending(db, pending_id)
    if pending is None:
        return None
    note_in = NoteCreate(
        title=pending.title,
        content=pending.content,
        note_type=pending.note_type,
        tool=pending.tool,
        project=pending.project,
        topic=pending.topic,
    )
    note = await create_note(db, note_in)  # embeds the final text, inserts into notes, commits
    await db.delete(pending)
    await db.commit()
    logger.info("Approved pending note %s -> note %s", pending_id, note.id)
    return note


async def reject_pending(db: AsyncSession, pending_id: uuid.UUID) -> bool:
    pending = await get_pending(db, pending_id)
    if pending is None:
        return False
    await db.delete(pending)
    await db.commit()
    logger.info("Rejected pending note %s", pending_id)
    return True
