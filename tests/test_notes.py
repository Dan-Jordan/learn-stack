import pytest
from httpx import AsyncClient

NOTE_PAYLOAD = {
    "title": "dbt seed loads static CSV data into the database",
    "content": "Run `dbt seed` to load CSV files from the seeds/ directory into the database as tables. Useful for reference data like state codes or test fixtures.",
    "note_type": "command",
    "tool": "dbt",
    "topic": "data loading",
    "project": "healthcare_claims_dbt",
}


async def test_create_note(client: AsyncClient):
    response = await client.post("/notes", json=NOTE_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == NOTE_PAYLOAD["title"]
    assert data["note_type"] == "command"
    assert data["tool"] == "dbt"
    assert "id" in data
    assert "created_at" in data


async def test_get_note(client: AsyncClient):
    created = (await client.post("/notes", json=NOTE_PAYLOAD)).json()
    response = await client.get(f"/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_note_not_found(client: AsyncClient):
    response = await client.get("/notes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_list_notes(client: AsyncClient):
    await client.post("/notes", json=NOTE_PAYLOAD)
    await client.post("/notes", json={**NOTE_PAYLOAD, "title": "second note"})
    response = await client.get("/notes")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_keyword_search_match(client: AsyncClient):
    await client.post("/notes", json=NOTE_PAYLOAD)
    await client.post("/notes", json={**NOTE_PAYLOAD, "title": "Docker basics", "content": "unrelated content"})
    results = (await client.get("/notes?q=dbt")).json()
    assert len(results) == 1
    assert "dbt" in results[0]["title"].lower()


async def test_keyword_search_no_match(client: AsyncClient):
    await client.post("/notes", json=NOTE_PAYLOAD)
    response = await client.get("/notes?q=zzznomatch")
    assert response.status_code == 200
    assert response.json() == []


async def test_update_note(client: AsyncClient):
    created = (await client.post("/notes", json=NOTE_PAYLOAD)).json()
    response = await client.put(f"/notes/{created['id']}", json={"title": "updated title"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "updated title"
    assert data["content"] == NOTE_PAYLOAD["content"]
    assert data["updated_at"] >= data["created_at"]


async def test_update_note_not_found(client: AsyncClient):
    response = await client.put(
        "/notes/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )
    assert response.status_code == 404


async def test_delete_note(client: AsyncClient):
    created = (await client.post("/notes", json=NOTE_PAYLOAD)).json()
    response = await client.delete(f"/notes/{created['id']}")
    assert response.status_code == 204
    assert (await client.get(f"/notes/{created['id']}")).status_code == 404


async def test_delete_note_not_found(client: AsyncClient):
    response = await client.delete("/notes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
