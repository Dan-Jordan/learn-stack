import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.note import NoteType


class NoteCreate(BaseModel):
    title: str
    content: str
    note_type: NoteType
    tool: str | None = None
    project: str | None = None
    topic: str | None = None


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
