import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

TEST_USERNAME = "learnstack-test-user"
TEST_PASSWORD = "learnstack-test-pass"


@pytest.fixture
async def unauthenticated_client(engine, monkeypatch):
    """A client hitting the *real* auth dependency — `client` in conftest.py overrides it away.

    Reuses the shared `engine` fixture (only `get_db` is overridden, matching conftest's
    pattern) so routes that touch the DB still work once credentials are supplied.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    monkeypatch.setenv("BASIC_AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", TEST_PASSWORD)

    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def test_protected_route_no_credentials(unauthenticated_client):
    response = await unauthenticated_client.get("/notes")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


async def test_protected_route_wrong_credentials(unauthenticated_client):
    response = await unauthenticated_client.get("/notes", auth=("wronguser", "wrongpass"))
    assert response.status_code == 401


async def test_protected_route_correct_credentials(unauthenticated_client):
    response = await unauthenticated_client.get("/notes", auth=(TEST_USERNAME, TEST_PASSWORD))
    assert response.status_code == 200


async def test_root_requires_auth(unauthenticated_client):
    response = await unauthenticated_client.get("/")
    assert response.status_code == 401

    response = await unauthenticated_client.get("/", auth=(TEST_USERNAME, TEST_PASSWORD))
    assert response.status_code == 200


async def test_health_has_no_auth_required(unauthenticated_client):
    response = await unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_docs_and_openapi_require_auth(unauthenticated_client):
    assert (await unauthenticated_client.get("/docs")).status_code == 401
    assert (await unauthenticated_client.get("/openapi.json")).status_code == 401

    response = await unauthenticated_client.get(
        "/openapi.json", auth=(TEST_USERNAME, TEST_PASSWORD)
    )
    assert response.status_code == 200
