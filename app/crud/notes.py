import uuid
from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def create_note(db: AsyncSession, note_in: NoteCreate) -> Note:
    note = Note(**note_in.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_note(db: AsyncSession, note_id: uuid.UUID) -> Note | None:
    result = await db.execute(select(Note).where(Note.id == note_id))
    return result.scalar_one_or_none()


async def get_notes(
    db: AsyncSession,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Note]:
    stmt = select(Note)
    if q:
        stmt = stmt.where(
            or_(
                Note.title.ilike(f"%{q}%"),
                Note.content.ilike(f"%{q}%"),
            )
        )
    stmt = stmt.order_by(Note.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_note(
    db: AsyncSession, note_id: uuid.UUID, note_in: NoteUpdate
) -> Note | None:
    note = await get_note(db, note_id)
    if note is None:
        return None
    for field, value in note_in.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    note.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note_id: uuid.UUID) -> bool:
    note = await get_note(db, note_id)
    if note is None:
        return False
    await db.delete(note)
    await db.commit()
    return True
