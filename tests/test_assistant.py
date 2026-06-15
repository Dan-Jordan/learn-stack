"""Tests for the Phase 11 notes assistant agent loop (POST /chat).

The loop in app/assistant.py drives the Anthropic client directly, so these tests
mock `app.assistant._client` to return scripted tool-use / text responses across
loop iterations, and mock `app.assistant.notes_crud.search_notes_semantic` so no
real DB or embedding calls happen. Patch targets are the names as used inside
app.assistant (the importing module), per the project's testing convention.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.assistant import MAX_ITERATIONS


# --- helpers to build fake Anthropic response objects -----------------------

def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(name, tool_input, id="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=id)


def make_response(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


def make_client(responses):
    """Fake AsyncAnthropic whose messages.create yields `responses` in order."""
    create = AsyncMock(side_effect=responses)
    fake = SimpleNamespace(messages=SimpleNamespace(create=create))
    return fake, create


# --- tests ------------------------------------------------------------------

async def test_direct_reply_no_tool(client: AsyncClient):
    """Model answers in text on the first turn — loop returns immediately."""
    fake, create = make_client([make_response("end_turn", [text_block("Hello!")])])
    with patch("app.assistant._client", return_value=fake):
        resp = await client.post("/chat", json={"message": "hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Hello!"
    assert body["trace"] == []
    assert create.call_count == 1


async def test_search_then_answer(client: AsyncClient):
    """tool_use → dispatch search → tool_result → text answer (two model calls)."""
    note = SimpleNamespace(title="Docker --rm", content="Use docker run --rm")
    responses = [
        make_response("tool_use", [tool_block("search_notes", {"query": "docker"})]),
        make_response("end_turn", [text_block("You noted: use docker run --rm.")]),
    ]
    fake, create = make_client(responses)
    with patch("app.assistant._client", return_value=fake), patch(
        "app.assistant.notes_crud.search_notes_semantic",
        new=AsyncMock(return_value=[(note, 0.91)]),
    ) as search:
        resp = await client.post("/chat", json={"message": "what did I note about docker?"})
    body = resp.json()
    assert body["reply"] == "You noted: use docker run --rm."
    assert search.call_count == 1
    assert create.call_count == 2
    assert len(body["trace"]) == 1
    assert body["trace"][0]["tool"] == "search_notes"
    assert body["trace"][0]["input"] == {"query": "docker"}


async def test_create_note_is_not_persisted(client: AsyncClient):
    """create_note is confirm-before-save: proposed in the trace, never written."""
    draft = {
        "title": "Render needs plan: free",
        "content": "Set `plan: free` or Render defaults to Starter.",
        "note_type": "error_fix",
        "tool": "Render",
        "topic": "deployment",
    }
    responses = [
        make_response("tool_use", [tool_block("create_note", draft, id="toolu_c")]),
        make_response("end_turn", [text_block("I drafted a note for you to review and save.")]),
    ]
    fake, create = make_client(responses)
    with patch("app.assistant._client", return_value=fake):
        resp = await client.post("/chat", json={"message": "save a note about render plan free"})
    body = resp.json()
    assert body["reply"].startswith("I drafted")
    assert len(body["trace"]) == 1
    assert body["trace"][0]["tool"] == "create_note"
    assert body["trace"][0]["input"] == draft
    # The draft was proposed, not written to the DB.
    notes = await client.get("/notes")
    assert notes.json() == []
    assert create.call_count == 2


async def test_history_is_forwarded(client: AsyncClient):
    """Client-supplied history is prepended before the new user message."""
    fake, create = make_client([make_response("end_turn", [text_block("yes")])])
    history = [
        {"role": "user", "content": "remember 42"},
        {"role": "assistant", "content": "noted"},
    ]
    with patch("app.assistant._client", return_value=fake):
        resp = await client.post("/chat", json={"message": "what number?", "history": history})
    assert resp.status_code == 200
    sent = create.call_args.kwargs["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[-1] == {"role": "user", "content": "what number?"}


async def test_iteration_cap(client: AsyncClient):
    """Model that never stops calling tools is capped at MAX_ITERATIONS."""
    responses = [
        make_response("tool_use", [text_block("searching"), tool_block("search_notes", {"query": "x"})])
        for _ in range(MAX_ITERATIONS)
    ]
    fake, create = make_client(responses)
    with patch("app.assistant._client", return_value=fake), patch(
        "app.assistant.notes_crud.search_notes_semantic", new=AsyncMock(return_value=[])
    ) as search:
        resp = await client.post("/chat", json={"message": "loop"})
    body = resp.json()
    assert "tool-iteration limit" in body["reply"]
    assert create.call_count == MAX_ITERATIONS
    assert search.call_count == MAX_ITERATIONS


async def test_empty_message_returns_422(client: AsyncClient):
    resp = await client.post("/chat", json={"message": ""})
    assert resp.status_code == 422
