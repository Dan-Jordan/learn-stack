"""Local (stdio) MCP server exposing LearnStack's notes tools — Phase 15.

Built on the low-level ``mcp.server.Server`` (not FastMCP) so the tool definitions reuse the
shared schema dicts from ``app.prompts`` / ``app.schemas.note`` verbatim — the same schema the
``/chat`` and ``/draft`` Anthropic tools already use — rather than a second schema generated
from a function signature. FastMCP can only derive a schema *from* a typed function; it can't
consume our pre-existing dict, so it would create a second source of truth for the note shape.
See the Phase 15 decisions log in CLAUDE.md.

Two tools are registered: ``search_notes`` (read-only) and ``create_note`` (a *staged* write —
it inserts into ``pending_notes``, never ``notes`` directly, and never embeds). A staged note is
reviewed, edited, and approved in the web-UI "Pending" tab before it is promoted into ``notes``;
that gate is why an agentic host can be given a write tool without writing straight to the
system of record.

Transport is stdio: **stdout carries the JSON-RPC protocol**, so all logging must go to stderr
(configured in ``main``) or it corrupts the channel. The DB target follows ``DATABASE_URL``
(loaded from ``.env`` when ``app.database`` is imported), so pointing it at Neon captures into
the system-of-record database.
"""

import asyncio
import logging
import sys

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.crud import notes as notes_crud
from app.crud import pending as pending_crud
from app.database import AsyncSessionLocal
from app.schemas.note import NoteCreate, NOTE_TOOL_INPUT_SCHEMA
from app.prompts import SEARCH_NOTES_TOOL, CREATE_NOTE_TRIGGER, NOTE_QUALITY_GUIDANCE

logger = logging.getLogger(__name__)

server = Server("learnstack")

# create_note's *behavior* sentence is MCP-specific (stages a pending row for review), so it lives
# here; the shared trigger and quality policy come from app.prompts, and the input schema is the
# shared NOTE_TOOL_INPUT_SCHEMA. Unlike /chat, an MCP server can't set the host's system prompt, so
# NOTE_QUALITY_GUIDANCE rides on the tool description here instead.
_CREATE_NOTE_TOOL = {
    "name": "create_note",
    "description": (
        "Capture a new technical note for the user. The note is staged for review — it is added "
        "to the LearnStack knowledge base only after the user reviews and approves it in the "
        "Pending tab, not immediately. " + CREATE_NOTE_TRIGGER + " " + NOTE_QUALITY_GUIDANCE
    ),
    "input_schema": NOTE_TOOL_INPUT_SCHEMA,
}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Advertise the tools this server exposes (MCP tool discovery).

    The shared dict keys the JSON schema under ``input_schema`` (the Anthropic Messages API
    spelling); MCP's ``types.Tool`` spells it ``inputSchema``. We reuse the schema *value* and
    the name/description, re-keying only the wrapper — so the contract stays a single artifact.
    """
    return [
        types.Tool(
            name=SEARCH_NOTES_TOOL["name"],
            description=SEARCH_NOTES_TOOL["description"],
            inputSchema=SEARCH_NOTES_TOOL["input_schema"],
        ),
        types.Tool(
            name=_CREATE_NOTE_TOOL["name"],
            description=_CREATE_NOTE_TOOL["description"],
            inputSchema=_CREATE_NOTE_TOOL["input_schema"],
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch a tool invocation. Input is validated against inputSchema by the SDK first."""
    if name == "search_notes":
        return await _search_notes(arguments)
    if name == "create_note":
        return await _create_note(arguments)
    raise ValueError(f"Unknown tool: {name}")


async def _search_notes(arguments: dict) -> list[types.TextContent]:
    query = arguments["query"]
    limit = arguments.get("limit", 5)
    # INFO: one discrete operation per call. Size/limit only, never the query text (never log values).
    logger.info("MCP search_notes called (limit=%d)", limit)

    # The stdio server is one long-lived process, not per-request, so each tool call opens a fresh
    # session here (and in _create_note below) rather than holding one open — mirrors FastAPI's
    # per-request session, minus the request.
    async with AsyncSessionLocal() as db:
        results = await notes_crud.search_notes_semantic(db, query, limit)

    if not results:
        return [types.TextContent(type="text", text="No matching notes found.")]

    text = "\n\n".join(
        f"[Note: {note.title}] (similarity {score:.2f})\n{note.content}"
        for note, score in results
    )
    return [types.TextContent(type="text", text=text)]


async def _create_note(arguments: dict) -> list[types.TextContent]:
    # NoteCreate applies Pydantic validation (required fields, note_type enum) on top of the
    # SDK's schema check, and gives create_pending the exact contract it expects.
    note_in = NoteCreate(**arguments)
    # Type only — never the title/content (never log values), consistent with the crud layer.
    logger.info("MCP create_note called (type=%s)", note_in.note_type.value)

    async with AsyncSessionLocal() as db:
        pending = await pending_crud.create_pending(db, note_in)

    # The host shows this text back; make the staged/pending state explicit so the model doesn't
    # claim the note is saved, and tell it not to re-stage the same note.
    return [
        types.TextContent(
            type="text",
            text=(
                f"Note staged for review (id {pending.id}). It is pending in LearnStack and will "
                "be added to the notes only after the user approves it in the Pending tab. Do not "
                "call create_note again for this same note."
            ),
        )
    ]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    # stdout is the protocol channel — send logs to stderr so they never corrupt it.
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
