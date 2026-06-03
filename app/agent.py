import os
from anthropic import AsyncAnthropic
from app.schemas.note import NoteCreate
from app.models.note import NoteType


def _client() -> AsyncAnthropic:
    # Function (not module-level) so the SDK doesn't read ANTHROPIC_API_KEY at import time.
    return AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


_DRAFT_TOOL = {
    "name": "create_note",
    "description": (
        "Extract a structured technical note from raw content. "
        "Clean and reformat the content as concise Markdown."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short descriptive title for the note",
            },
            "content": {
                "type": "string",
                "description": "Note body as clean Markdown",
            },
            "note_type": {
                "type": "string",
                "enum": [t.value for t in NoteType],
                "description": "Best-fit category for this content",
            },
            "tool": {
                "type": "string",
                "description": "Primary tool or technology (e.g. dbt, Docker, SQLAlchemy). Omit if not applicable.",
            },
            "topic": {
                "type": "string",
                "description": "Subject area (e.g. CI/CD, testing, migrations). Omit if not applicable.",
            },
            "project": {
                "type": "string",
                "description": "Project name this note relates to. Omit if not applicable.",
            },
        },
        "required": ["title", "content", "note_type"],
    },
}


async def draft_note(raw_content: str) -> NoteCreate:
    message = await _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a technical knowledge assistant. "
            "Given raw content, extract a structured note using the create_note tool. "
            "Rewrite the content as clean, concise Markdown. "
            "Choose the most specific note_type that fits."
        ),
        tools=[_DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "create_note"},
        messages=[{"role": "user", "content": raw_content}],
    )

    tool_use = next(b for b in message.content if b.type == "tool_use")
    inputs = tool_use.input

    return NoteCreate(
        title=inputs["title"],
        content=inputs["content"],
        note_type=NoteType(inputs["note_type"]),
        tool=inputs.get("tool"),
        topic=inputs.get("topic"),
        project=inputs.get("project"),
    )
