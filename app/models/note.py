import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base


class NoteType(str, enum.Enum):
    technical_note = "technical_note"
    command = "command"
    error_fix = "error_fix"
    project_note = "project_note"
    concept = "concept"
    question = "question"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[NoteType] = mapped_column(Enum(NoteType), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project: Mapped[str | None] = mapped_column(String(200), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # nullable=True because this column was added via migration to a table with pre-existing rows.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)


class PendingNote(Base):
    """A note captured via the MCP create_note tool, staged for human review before promotion.

    Mirrors only the writable NoteCreate fields — deliberately **no embedding column**, because a
    pending note is never embedded. Embedding happens once, at approval, on the final text, when
    crud.create_note promotes the row into the `notes` table. Kept as a separate table (not a
    `status` column on `notes`) so every `notes` row stays a real, approved, embedded note and no
    read path has to know "pending" exists. No `updated_at`: editing a pending note is a cheap
    text UPDATE, and the row is short-lived (approved or rejected, then deleted).
    """

    __tablename__ = "pending_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[NoteType] = mapped_column(Enum(NoteType), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project: Mapped[str | None] = mapped_column(String(200), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
