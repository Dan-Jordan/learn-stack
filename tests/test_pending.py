import uuid

from sqlalchemy import select

from app.crud import pending as pending_crud
from app.models.note import Note, PendingNote, NoteType
from app.schemas.note import NoteCreate


async def _seed(db_session, **overrides) -> PendingNote:
    """Stage a pending note directly (there is no HTTP create path for pending notes)."""
    data = {
        "title": "Neon SSL gotcha",
        "content": "asyncpg rejects sslmode in the URL; pass ssl via connect_args.",
        "note_type": NoteType.error_fix,
        "tool": "asyncpg",
        "project": "learnstack",
        "topic": "database",
    }
    data.update(overrides)
    return await pending_crud.create_pending(db_session, NoteCreate(**data))


async def test_list_pending_empty(client):
    resp = await client.get("/pending")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_pending_returns_staged(client, db_session):
    await _seed(db_session, title="First")
    await _seed(db_session, title="Second")

    resp = await client.get("/pending")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Response shape: has created_at, but not updated_at or embedding (per PendingNoteResponse).
    item = body[0]
    assert "created_at" in item
    assert "updated_at" not in item
    assert "embedding" not in item
    assert {b["title"] for b in body} == {"First", "Second"}


async def test_update_pending(client, db_session):
    pending = await _seed(db_session, title="Old title")

    resp = await client.put(f"/pending/{pending.id}", json={"title": "New title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"

    # Unset fields are untouched (partial update via NoteUpdate/exclude_unset).
    assert resp.json()["content"].startswith("asyncpg rejects")


async def test_update_pending_not_found(client):
    resp = await client.put(f"/pending/{uuid.uuid4()}", json={"title": "x"})
    assert resp.status_code == 404


async def test_approve_pending_promotes_and_embeds(client, db_session):
    pending = await _seed(db_session, title="Promote me")

    resp = await client.post(f"/pending/{pending.id}/approve")
    assert resp.status_code == 201
    note_id = uuid.UUID(resp.json()["id"])
    assert resp.json()["title"] == "Promote me"

    # The promoted note exists in `notes` and was embedded (mock_embeddings stands in for OpenAI).
    note = await db_session.get(Note, note_id)
    assert note is not None
    assert note.embedding is not None

    # The pending row is gone.
    remaining = (await db_session.execute(select(PendingNote))).scalars().all()
    assert remaining == []


async def test_approve_pending_not_found(client):
    resp = await client.post(f"/pending/{uuid.uuid4()}/approve")
    assert resp.status_code == 404


async def test_reject_pending(client, db_session):
    pending = await _seed(db_session)

    resp = await client.delete(f"/pending/{pending.id}")
    assert resp.status_code == 204

    remaining = (await db_session.execute(select(PendingNote))).scalars().all()
    assert remaining == []


async def test_reject_pending_not_found(client):
    resp = await client.delete(f"/pending/{uuid.uuid4()}")
    assert resp.status_code == 404
