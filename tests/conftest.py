import hashlib
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.auth import get_current_user
from app.database import get_db, Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/learnstack_test",
)

EMBEDDING_DIM = 1536


def _fake_embedding(text: str) -> list[float]:
    """Deterministic stand-in for the OpenAI embedding call — no network, no key.

    Maps content to a stable 1536-dim vector so the pgvector write and
    cosine-distance query paths are fully exercised, but it encodes no real
    semantics. Components are non-negative (bytes / 255), which keeps cosine
    distance in [0, 1] and therefore similarity scores (1 - distance) in the
    [0, 1] range the tests assert. Tests that need exact ranking inject their
    own controlled vectors (see test_semantic_query_ranking).
    """
    out: list[float] = []
    counter = 0
    base = text.encode("utf-8")
    while len(out) < EMBEDDING_DIM:
        block = hashlib.sha256(base + counter.to_bytes(4, "little")).digest()
        out.extend(b / 255.0 for b in block)
        counter += 1
    return out[:EMBEDDING_DIM]


@pytest.fixture(autouse=True)
def mock_embeddings():
    """Patch the live OpenAI embedding call out of the entire suite.

    A single seam — `app.crud.notes.embed_text` — feeds both the note-write and
    the semantic-query paths, so patching it here removes every live OpenAI call
    from the tests. That keeps the suite (and CI) deterministic, free, and free
    of secrets, so every test runs on every PR. A test that needs specific
    embedding values (e.g. ranking) patches `embed_text` again locally with
    controlled vectors; the inner patch wins while active.
    """
    with patch("app.crud.notes.embed_text", new=AsyncMock(side_effect=_fake_embedding)):
        yield


@pytest.fixture
async def engine():
    """One engine per test: create the schema empty, hand it out, drop it on teardown.

    Shared by `client` and `db_session` so requests and directly-seeded rows hit the same DB —
    needed for paths with no HTTP create endpoint (e.g. pending notes are staged only via MCP).
    """
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(engine):
    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    async def override_get_current_user():
        return "test-user"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(engine):
    """A session on the same engine as `client`, for seeding/asserting DB state directly."""
    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session
