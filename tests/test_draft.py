import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.schemas.note import NoteCreate


DRAFT_RESULT = NoteCreate(
    title="SQLAlchemy async session management",
    content="Use `async_sessionmaker` to create sessions. Each request gets its own session via dependency injection.",
    note_type="technical_note",
    tool="SQLAlchemy",
    topic="database",
    project=None,
)

RAW_CONTENT = (
    "sqlalchemy async sessions — use async_sessionmaker, inject per request, "
    "always commit or rollback before closing"
)


async def test_draft_response_shape(client: AsyncClient):
    with patch("app.routers.draft.draft_note", new_callable=AsyncMock, return_value=DRAFT_RESULT):
        response = await client.post("/draft", json={"content": RAW_CONTENT})
    assert response.status_code == 200
    assert "draft" in response.json()


async def test_draft_note_called_once(client: AsyncClient):
    with patch("app.routers.draft.draft_note", new_callable=AsyncMock, return_value=DRAFT_RESULT) as mock_agent:
        await client.post("/draft", json={"content": RAW_CONTENT})
    mock_agent.assert_called_once()


async def test_draft_returns_required_fields(client: AsyncClient):
    with patch("app.routers.draft.draft_note", new_callable=AsyncMock, return_value=DRAFT_RESULT):
        response = await client.post("/draft", json={"content": RAW_CONTENT})
    draft = response.json()["draft"]
    for field in ("title", "content", "note_type"):
        assert field in draft
        assert draft[field]


async def test_draft_optional_fields_nullable(client: AsyncClient):
    minimal = NoteCreate(
        title="A note",
        content="Some content",
        note_type="concept",
    )
    with patch("app.routers.draft.draft_note", new_callable=AsyncMock, return_value=minimal):
        response = await client.post("/draft", json={"content": "some raw text"})
    draft = response.json()["draft"]
    assert draft["tool"] is None
    assert draft["topic"] is None
    assert draft["project"] is None


async def test_draft_empty_content_returns_422(client: AsyncClient):
    response = await client.post("/draft", json={"content": ""})
    assert response.status_code == 422


async def test_draft_note_type_is_valid_enum(client: AsyncClient):
    from app.models.note import NoteType
    with patch("app.routers.draft.draft_note", new_callable=AsyncMock, return_value=DRAFT_RESULT):
        response = await client.post("/draft", json={"content": RAW_CONTENT})
    note_type = response.json()["draft"]["note_type"]
    assert note_type in {t.value for t in NoteType}
