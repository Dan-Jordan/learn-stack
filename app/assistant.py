import os
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.note import NOTE_TOOL_INPUT_SCHEMA
from app.crud import notes as notes_crud

MODEL = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 5


def _client() -> AsyncAnthropic:
    # Function (not module-level) so the SDK doesn't read ANTHROPIC_API_KEY at import time.
    return AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


_SEARCH_NOTES_TOOL = {
    "name": "search_notes",
    "description": (
        "Search the user's saved technical notes by meaning (semantic search) and return "
        "the most relevant ones. Call this when the user asks a question their past notes "
        "might answer, or asks what they've written about a topic."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query describing what to find",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of notes to return (default 5)",
            },
        },
        "required": ["query"],
    },
}

_CREATE_NOTE_TOOL = {
    "name": "create_note",
        "description": (
            "Draft a new technical note for the user to review and save. This does NOT save the "
            "note — it proposes a draft that the user confirms and saves manually, keeping junk "
            "out of the knowledge base. Call this when the user asks to capture, save, or note "
            "something."
        ),
    "input_schema": NOTE_TOOL_INPUT_SCHEMA,
}

_TOOLS = [_SEARCH_NOTES_TOOL, _CREATE_NOTE_TOOL]

_SYSTEM = (
    "You are LearnStack's notes assistant. You help the user search their saved technical "
    "notes and capture new ones. You have two tools — search_notes and create_note — and you "
    "decide turn by turn which to use, if any.\n\n"
    "To answer a question from the user's own history, call search_notes first, then answer "
    "using only what you find, citing notes by title. If the search returns nothing relevant, "
    "say so rather than answering from general knowledge.\n\n"
    "To capture something, call create_note. The draft is shown to the user to review and "
    "save — it is not saved automatically — so describe what you drafted rather than claiming "
    "it is saved. Prioritize content worth retrieving later: project-specific facts, configs, "
    "gotchas, errors and their fixes, and decisions with the reasoning behind them — the kind "
    "of detail that fades from memory and would otherwise be re-debugged or re-decided. Trim "
    "general concept explanations the user already understands or could easily re-look-up.\n\n"
    "If no tool is needed, just reply directly."
)


async def _run_search(db: AsyncSession, tool_input: dict) -> tuple[str, int]:
    query = tool_input["query"]
    limit = tool_input.get("limit", 5)
    results = await notes_crud.search_notes_semantic(db, query, limit)
    if not results:
        return "No matching notes found.", 0
    text = "\n\n".join(
        f"[Note: {note.title}] (similarity {score:.2f})\n{note.content}"
        for note, score in results
    )
    return text, len(results)


async def run_assistant(messages: list[dict], db: AsyncSession) -> tuple[str, list[dict]]:
    """Run the multi-tool agent loop over a conversation.

    `messages` is the Anthropic-format conversation (user/assistant turns). Returns the
    final assistant text plus a trace of the tools the model called this turn. create_note
    is human-in-the-loop: the proposed draft is recorded in the trace and surfaced to the
    user for manual save, never persisted here.
    """
    # Copy so we don't mutate the caller's list while appending tool turns.
    messages = list(messages)
    trace: list[dict] = []
    response = None

    for _ in range(MAX_ITERATIONS):
        response = await _client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text, trace

        # Preserve the assistant turn (including tool_use blocks) before answering it.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                if block.name == "search_notes":
                    result_text, count = await _run_search(db, block.input)
                    trace.append(
                        {"tool": "search_notes", "input": block.input, "summary": f"{count} note(s) found"}
                    )
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                    )
                elif block.name == "create_note":
                    # Confirm-before-save: record the draft, do not persist.
                    trace.append(
                        {"tool": "create_note", "input": block.input, "summary": "draft proposed for review"}
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                "Draft prepared and shown to the user for review. It is NOT saved "
                                "yet — the user will save it manually. Do not call create_note "
                                "again for this same note."
                            ),
                        }
                    )
                else:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Unknown tool: {block.name}",
                            "is_error": True,
                        }
                    )
            except Exception as exc:
                # A single tool failure (bad tool input, DB/embedding error) should not 500 the
                # whole conversation — hand the error back so the model can recover or explain.
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Tool {block.name} failed: {exc}",
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    # Iteration cap hit — return whatever text the last response carried, flagged.
    text = next((b.text for b in response.content if b.type == "text"), "")
    note = "(Stopped after reaching the tool-iteration limit.)"
    return (f"{text}\n\n{note}" if text else note), trace
