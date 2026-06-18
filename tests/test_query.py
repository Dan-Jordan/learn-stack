from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _unit_vector(index: int, dim: int = 1536) -> list[float]:
    vec = [0.0] * dim
    vec[index] = 1.0
    return vec

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
    # Deterministic test of MY ranking/scoring code (closest vector first,
    # score = 1 - cosine_distance) using controlled embeddings — no live API.
    # The query shares its vector with the SQLAlchemy note (distance 0 -> score 1.0);
    # the Docker note is orthogonal (distance 1 -> score 0.0). Verifies the query
    # path orders by distance and computes scores correctly.
    query = "which note is closest"
    vectors = {
        SQLALCHEMY_NOTE["content"]: _unit_vector(0),
        DOCKER_NOTE["content"]: _unit_vector(1),
        query: _unit_vector(0),
    }

    async def fake_embed(text: str) -> list[float]:
        return vectors[text]

    # Patch over the suite-wide stub so creates AND the query use these vectors.
    with patch("app.crud.notes.embed_text", new=AsyncMock(side_effect=fake_embed)):
        await client.post("/notes", json=SQLALCHEMY_NOTE)
        await client.post("/notes", json=DOCKER_NOTE)
        results = (await client.post("/query", json={"q": query})).json()

    assert len(results) == 2
    # The SQLAlchemy note (identical vector) ranks above the orthogonal Docker note.
    assert results[0]["title"] == SQLALCHEMY_NOTE["title"]
    assert results[1]["title"] == DOCKER_NOTE["title"]
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["score"] == pytest.approx(0.0)


async def test_semantic_query_respects_limit(client: AsyncClient):
    for i in range(5):
        await client.post("/notes", json={**SQLALCHEMY_NOTE, "title": f"Note {i}"})
    results = (await client.post("/query", json={"q": "SQLAlchemy session", "limit": 3})).json()
    assert len(results) == 3
