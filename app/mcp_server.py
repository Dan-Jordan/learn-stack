"""Local (stdio) MCP server exposing LearnStack's notes tools — Phase 15.

Built on the low-level ``mcp.server.Server`` (not FastMCP) so the tool definitions reuse the
shared schema dicts from ``app.prompts`` / ``app.schemas.note`` verbatim — the same schema the
``/chat`` and ``/draft`` Anthropic tools already use — rather than a second schema generated
from a function signature. FastMCP can only derive a schema *from* a typed function; it can't
consume our pre-existing dict, so it would create a second source of truth for the note shape.
See the Phase 15 decisions log in CLAUDE.md.

Read-only for now: only ``search_notes`` is registered. ``create_note`` (a staged write to the
``pending_notes`` table) is added in a later step of this phase.

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
from app.database import AsyncSessionLocal
from app.prompts import SEARCH_NOTES_TOOL

logger = logging.getLogger(__name__)

server = Server("learnstack")


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
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch a tool invocation. Input is validated against inputSchema by the SDK first."""
    if name != "search_notes":
        raise ValueError(f"Unknown tool: {name}")

    query = arguments["query"]
    limit = arguments.get("limit", 5)
    # INFO: one discrete operation per call. Size/limit only, never the query text (never log values).
    logger.info("MCP search_notes called (limit=%d)", limit)

    # The stdio server is one long-lived process, so open a fresh session per call rather than
    # holding one open (mirrors FastAPI's per-request session, minus the request).
    async with AsyncSessionLocal() as db:
        results = await notes_crud.search_notes_semantic(db, query, limit)

    if not results:
        return [types.TextContent(type="text", text="No matching notes found.")]

    text = "\n\n".join(
        f"[Note: {note.title}] (similarity {score:.2f})\n{note.content}"
        for note, score in results
    )
    return [types.TextContent(type="text", text=text)]


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
