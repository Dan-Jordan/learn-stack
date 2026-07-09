import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.models.note import NoteType


class NoteCreate(BaseModel):
    title: str
    content: str
    note_type: NoteType
    tool: str | None = None
    project: str | None = None
    topic: str | None = None


# Shared tool input schema for `create_note`, used by app/agent.py (/draft), app/assistant.py
# (/chat), and app/mcp_server.py (MCP create_note) — one source of truth so the note shape
# can't drift across those three callers. Kept beside NoteCreate above, not in app/prompts.py
# with the tool-steering prose, because it mirrors NoteCreate's writable fields — two views of
# one note shape kept adjacent so they can't drift from the model either. Per-field
# descriptions live here; each caller supplies its own top-level tool `description` and
# re-keys this value (`input_schema` for Anthropic, `inputSchema` for MCP's types.Tool).
NOTE_TOOL_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short descriptive title for the note"},
        "content": {"type": "string", "description": "Note body as clean, concise Markdown"},
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
            "description": "Project this note relates to. Omit if not applicable.",
        },
    },
    "required": ["title", "content", "note_type"],
}


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    note_type: NoteType | None = None
    tool: str | None = None
    project: str | None = None
    topic: str | None = None


class NoteResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    note_type: NoteType
    tool: str | None
    project: str | None
    topic: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryRequest(BaseModel):
    q: str
    limit: int = 10


class QueryResult(NoteResponse):
    score: float


class AskRequest(BaseModel):
    q: str
    limit: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[NoteResponse]


class DraftRequest(BaseModel):
    content: str = Field(min_length=1)


class DraftResponse(BaseModel):
    draft: NoteCreate


class ChatMessage(BaseModel):
    """One prior turn of conversation, supplied by the client (stateless)."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class ToolCall(BaseModel):
    """One tool the agent invoked this turn, for the response trace.

    `input` is the raw tool input the model produced. For create_note it is the
    proposed (unsaved) draft — the UI reads it to offer a manual save.
    """

    tool: str
    input: dict[str, Any]
    summary: str | None = None


class ChatResponse(BaseModel):
    reply: str
    trace: list[ToolCall]


class PendingNoteResponse(BaseModel):
    """A note staged via the MCP create_note tool, awaiting review in the Pending tab.

    Mirrors NoteResponse minus `updated_at` (the model has none — a pending row is short-lived
    and edits are cheap text UPDATEs) and minus any embedding (a pending note is never embedded).
    The pending write/edit contracts are the existing NoteCreate / NoteUpdate — a pending note's
    writable shape *is* NoteCreate by design, so no separate create/update schema is needed.
    """

    id: uuid.UUID
    title: str
    content: str
    note_type: NoteType
    tool: str | None
    project: str | None
    topic: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
