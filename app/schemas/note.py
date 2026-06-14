import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.note import NoteType


class NoteCreate(BaseModel):
    title: str
    content: str
    note_type: NoteType
    tool: str | None = None
    project: str | None = None
    topic: str | None = None


# Shared Anthropic tool input schema for the `create_note` tool, used by both the draft
# agent (app/agent.py) and the notes assistant (app/assistant.py). Mirrors NoteCreate's
# writable fields — kept here as the single source of truth for that tool contract so the
# two callers don't drift. Per-field descriptions live here (they describe the fields);
# each caller supplies its own top-level tool `description` for when/how to call it.
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
