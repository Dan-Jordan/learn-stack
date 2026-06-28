import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate
from app.embeddings import embed_text

logger = logging.getLogger(__name__)


async def create_note(db: AsyncSession, note_in: NoteCreate) -> Note:
    note = Note(**note_in.model_dump())
    note.embedding = await embed_text(note.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    # INFO state change; the id lets a later retrieval/citation be correlated back to this write.
    logger.info("Created note %s (type=%s)", note.id, note.note_type)
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
    updates = note_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(note, field, value)
    if "content" in updates:
        note.embedding = await embed_text(note.content)
    note.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)
    # Field names only (never the new values), plus whether the content change forced a re-embed.
    logger.info(
        "Updated note %s (fields=%s, re-embedded=%s)",
        note_id, sorted(updates), "content" in updates,
    )
    return note


async def delete_note(db: AsyncSession, note_id: uuid.UUID) -> bool:
    note = await get_note(db, note_id)
    if note is None:
        return False
    await db.delete(note)
    await db.commit()
    logger.info("Deleted note %s", note_id)
    return True


async def search_notes_semantic(
    db: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[tuple[Note, float]]:
    query_embedding = await embed_text(query)
    distance_expr = Note.embedding.cosine_distance(query_embedding)
    stmt = (
        select(Note, distance_expr.label("distance"))
        .where(Note.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    # cosine_distance returns 0 (identical) to 2 (opposite); subtract from 1 to get similarity score.
    results = [(note, 1 - distance) for note, distance in rows]
    # One log per search (shared by /query, /ask, and /chat). Zero results is a recoverable
    # oddity worth flagging — the downstream answer will be ungrounded — so WARNING, not INFO.
    if results:
        logger.info("Semantic search returned %d note(s)", len(results))
    else:
        logger.warning("Semantic search returned no notes")
    return results
