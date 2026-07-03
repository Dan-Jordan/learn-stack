"""Unit tests for the local MCP server's tool discovery and dispatch (app/mcp_server.py).

The low-level Server decorators leave `list_tools` / `call_tool` as plain coroutine functions, so
these call them directly. crud and the DB session are mocked — this tests *dispatch* (routing,
staging vs. searching, the response text), not the DB, which the crud tests already cover.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import app.mcp_server as mcp_server
from app.models.note import NoteType


class _FakeSession:
    """Stand-in for AsyncSessionLocal()'s context manager; crud is mocked so it's never used."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def test_list_tools_advertises_both_tools():
    tools = await mcp_server.list_tools()
    assert {t.name for t in tools} == {"search_notes", "create_note"}
    # The shared input_schema is re-keyed to MCP's inputSchema and carried through intact.
    create = next(t for t in tools if t.name == "create_note")
    assert "title" in create.inputSchema["properties"]
    assert create.inputSchema["required"] == ["title", "content", "note_type"]


async def test_create_note_stages_pending():
    pending_id = uuid.uuid4()
    fake_pending = SimpleNamespace(id=pending_id, note_type=NoteType.error_fix)
    args = {
        "title": "Neon SSL",
        "content": "pass ssl via connect_args",
        "note_type": "error_fix",
        "tool": "asyncpg",
    }
    with patch("app.mcp_server.AsyncSessionLocal", return_value=_FakeSession()), patch(
        "app.mcp_server.pending_crud.create_pending",
        new=AsyncMock(return_value=fake_pending),
    ) as mock_create:
        result = await mcp_server.call_tool("create_note", args)

    # Staged, not saved: the write went to create_pending, and the NoteCreate it received
    # matches the tool input (string note_type coerced to the enum).
    mock_create.assert_awaited_once()
    note_in = mock_create.await_args.args[1]
    assert note_in.title == "Neon SSL"
    assert note_in.note_type == NoteType.error_fix
    text = result[0].text
    assert str(pending_id) in text
    assert "pending" in text.lower()


async def test_create_note_validates_input():
    # Missing required note_type -> Pydantic raises before any DB work is attempted.
    with patch("app.mcp_server.pending_crud.create_pending", new=AsyncMock()) as mock_create:
        with pytest.raises(Exception):
            await mcp_server.call_tool("create_note", {"title": "x", "content": "y"})
    mock_create.assert_not_awaited()


async def test_search_notes_dispatches():
    note = SimpleNamespace(title="pgvector index", content="add ivfflat")
    with patch("app.mcp_server.AsyncSessionLocal", return_value=_FakeSession()), patch(
        "app.mcp_server.notes_crud.search_notes_semantic",
        new=AsyncMock(return_value=[(note, 0.87)]),
    ) as mock_search:
        result = await mcp_server.call_tool("search_notes", {"query": "pgvector"})

    mock_search.assert_awaited_once()
    text = result[0].text
    assert "pgvector index" in text
    assert "0.87" in text


async def test_search_notes_no_results():
    with patch("app.mcp_server.AsyncSessionLocal", return_value=_FakeSession()), patch(
        "app.mcp_server.notes_crud.search_notes_semantic",
        new=AsyncMock(return_value=[]),
    ):
        result = await mcp_server.call_tool("search_notes", {"query": "nothing"})

    assert result[0].text == "No matching notes found."


async def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        await mcp_server.call_tool("delete_everything", {})
