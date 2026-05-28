import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

SQLALCHEMY_NOTE = {
    "title": "SQLAlchemy async session management",
    "content": (
        "Use async_sessionmaker to create sessions. Each request gets its own session "
        "via dependency injection. Always commit or rollback before closing. "
        "The session is the unit of work — changes are tracked automatically."
    ),
    "note_type": "technical_note",
    "tool": "SQLAlchemy",
    "topic": "database",
}

DOCKER_NOTE = {
    "title": "Docker networking basics",
    "content": (
        "Containers on the same Docker network can reach each other by service name. "
        "Use bridge networks for local development. Expose ports with ports: in docker-compose."
    ),
    "note_type": "technical_note",
    "tool": "Docker",
    "topic": "networking",
}


async def test_ask_response_shape(client: AsyncClient):
    with patch("app.routers.ask.generate_answer", new_callable=AsyncMock, return_value="No notes found."):
        response = await client.post("/ask", json={"q": "SQLAlchemy"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data


async def test_ask_empty_db_returns_empty_sources(client: AsyncClient):
    with patch("app.routers.ask.generate_answer", new_callable=AsyncMock, return_value="No relevant notes."):
        response = await client.post("/ask", json={"q": "SQLAlchemy"})
    assert response.status_code == 200
    assert response.json()["sources"] == []


async def test_ask_returns_answer_and_sources(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    with patch("app.routers.ask.generate_answer", new_callable=AsyncMock, return_value="SQLAlchemy uses async sessions.") as mock_llm:
        response = await client.post("/ask", json={"q": "SQLAlchemy sessions"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "SQLAlchemy uses async sessions."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == SQLALCHEMY_NOTE["title"]
    mock_llm.assert_called_once()


async def test_ask_sources_have_required_fields(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    with patch("app.routers.ask.generate_answer", new_callable=AsyncMock, return_value="answer"):
        response = await client.post("/ask", json={"q": "database"})
    source = response.json()["sources"][0]
    for field in ("id", "title", "content", "note_type", "created_at", "updated_at"):
        assert field in source


async def test_ask_respects_limit(client: AsyncClient):
    for i in range(4):
        await client.post("/notes", json={**SQLALCHEMY_NOTE, "title": f"Note {i}"})
    with patch("app.routers.ask.generate_answer", new_callable=AsyncMock, return_value="answer"):
        response = await client.post("/ask", json={"q": "SQLAlchemy", "limit": 2})
    assert len(response.json()["sources"]) == 2
