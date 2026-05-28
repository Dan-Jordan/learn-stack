import pytest
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
        "Use bridge networks for local development. Expose ports with ports: in docker-compose. "
        "The host network mode skips isolation entirely."
    ),
    "note_type": "technical_note",
    "tool": "Docker",
    "topic": "networking",
}


async def test_semantic_query_empty_db(client: AsyncClient):
    response = await client.post("/query", json={"q": "SQLAlchemy session"})
    assert response.status_code == 200
    assert response.json() == []


async def test_semantic_query_returns_results(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    response = await client.post("/query", json={"q": "database session management"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == SQLALCHEMY_NOTE["title"]


async def test_semantic_query_result_has_score(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    results = (await client.post("/query", json={"q": "database session"})).json()
    assert "score" in results[0]
    assert 0.0 <= results[0]["score"] <= 1.0


async def test_semantic_query_result_has_note_fields(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    results = (await client.post("/query", json={"q": "database session"})).json()
    result = results[0]
    assert "id" in result
    assert "title" in result
    assert "content" in result
    assert "note_type" in result
    assert "created_at" in result


async def test_semantic_query_ranking(client: AsyncClient):
    await client.post("/notes", json=SQLALCHEMY_NOTE)
    await client.post("/notes", json=DOCKER_NOTE)
    results = (await client.post("/query", json={"q": "how do SQLAlchemy sessions work"})).json()
    assert len(results) == 2
    # The SQLAlchemy note should rank above the Docker note
    assert results[0]["title"] == SQLALCHEMY_NOTE["title"]
    assert results[0]["score"] > results[1]["score"]


async def test_semantic_query_respects_limit(client: AsyncClient):
    for i in range(5):
        await client.post("/notes", json={**SQLALCHEMY_NOTE, "title": f"Note {i}"})
    results = (await client.post("/query", json={"q": "SQLAlchemy session", "limit": 3})).json()
    assert len(results) == 3
