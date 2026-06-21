import logging
import os
from anthropic import AsyncAnthropic
from app.schemas.note import NoteCreate, NOTE_TOOL_INPUT_SCHEMA
from app.models.note import NoteType

logger = logging.getLogger(__name__)


def _client() -> AsyncAnthropic:
    # Function (not module-level) so the SDK doesn't read ANTHROPIC_API_KEY at import time.
    return AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


_DRAFT_TOOL = {
    "name": "create_note",
    "description": (
        "Extract a structured technical note from raw content. "
        "Clean and reformat the content as concise Markdown."
    ),
    "input_schema": NOTE_TOOL_INPUT_SCHEMA,
}


async def draft_note(raw_content: str) -> NoteCreate:
    # INFO: one discrete user-facing operation per /draft. Size only, not the raw content.
    logger.info("Drafting note from raw content (%d chars)", len(raw_content))
    message = await _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a technical knowledge assistant. "
            "Given raw content, extract a structured note using the create_note tool. "
            "Rewrite the content as clean, concise Markdown. "
            "Choose the most specific note_type that fits.\n\n"
            "This note will be retrieved later via semantic search, so prioritize "
            "what's worth retrieving: project-specific facts, configs, gotchas, "
            "errors and their fixes, and decisions along with the reasoning behind "
            "them — the kind of detail that fades from memory and would otherwise "
            "be re-debugged or re-decided later. Prefer note_type values like "
            "error_fix, technical_note, or project_note for this kind of content.\n\n"
            "Trim or de-emphasize general concept explanations that the reader "
            "already understands well enough to retain or re-look-up easily "
            "(e.g. how a standard library function or common pattern works in "
            "general). If the raw content is mostly general explanation with one "
            "specific gotcha or decision buried in it, focus the note on that "
            "specific part rather than reproducing the whole explanation."
        ),
        tools=[_DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "create_note"},
        messages=[{"role": "user", "content": raw_content}],
    )

    tool_use = next(b for b in message.content if b.type == "tool_use")
    inputs = tool_use.input

    logger.info("Drafted note (type=%s, title=%r)", inputs["note_type"], inputs.get("title"))
    return NoteCreate(
        title=inputs["title"],
        content=inputs["content"],
        note_type=NoteType(inputs["note_type"]),
        tool=inputs.get("tool"),
        topic=inputs.get("topic"),
        project=inputs.get("project"),
    )
