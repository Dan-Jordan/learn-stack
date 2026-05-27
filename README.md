# LearnStack

A personal technical knowledge system built from the ground up — designed to help you capture, organize, retrieve, and grow what you know.

## The vision

The destination is a **RAG-powered learning system**: a knowledge base you can have a conversation with. You ask "what have I learned about dbt testing?" or "what errors have I run into with Docker Compose?" and the system retrieves the relevant notes you actually wrote, grounds its answer in them, and cites its sources. Not a generic LLM response — a response drawn from your own captured experience.

That capability — Retrieval-Augmented Generation, or RAG — is built on a simple foundation: your notes get converted into vector embeddings that encode meaning, and when you ask a question the system finds the notes whose meaning is closest to your question and hands them to the model as context. The result is answers that are grounded in what *you* know, not just what the model was trained on.

LearnStack is not a second brain or an AI agent. It is a backend application that earns its complexity over time. But it is being built toward something specific: a system where your saved knowledge actively helps you keep learning.

---

## What it does today

- Save technical notes with structured metadata (type, tool, topic, project)
- Retrieve and search notes by keyword
- Full CRUD via a FastAPI REST API
- Postgres backend with schema managed by Alembic migrations
- Markdown-based note capture workflow for capturing learning before the API is running

---

## Why it exists

Technical learning tends to scatter. Notes live in chat windows, code comments, scratch files, and browser tabs. LearnStack gives that learning somewhere permanent and searchable to live — and is built in a way that reinforces the exact skills the notes are about.

The project serves two purposes simultaneously:

**Practical** — a real tool for capturing and retrieving what you are learning about Python, FastAPI, SQLAlchemy, dbt, Docker, Postgres, and data engineering.

**Educational** — a realistic application for practicing backend development, database modeling, API design, async Python, testing, migrations, and eventually RAG and semantic search.

---

## Tech stack

| Layer | Tool |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.x (async) |
| Schemas | Pydantic v2 |
| Migrations | Alembic |
| Environment | Docker Compose |
| Testing | pytest + httpx |
| Embeddings (Phase 4) | OpenAI text-embedding API + pgvector |

---

## Project phases

### Phase 1 — Basic notes app ✓
Full CRUD on technical notes. Keyword search. Postgres backend. Docker Compose. 10 passing tests.

### Phase 2 — Alembic migrations ✓
Replaced `create_all` on startup with Alembic migration scripts. Schema changes are now versioned and safe.

### Phase 3 — pgvector *(next)*
Add the pgvector Postgres extension and an `embedding` column to the notes table via Alembic migration. Foundation for semantic search.

### Phase 4 — Embedding pipeline
Generate and store vector embeddings when notes are created or updated using the OpenAI embedding API. Backfill existing notes.

### Phase 5 — Semantic search
`POST /query` takes a natural language question, embeds it, and returns notes ranked by meaning using pgvector similarity search.

### Phase 6 — LLM answer generation
Pass retrieved notes + question to an LLM. Return a grounded answer with citations drawn from your own captured knowledge.

### Phase 7 — Note drafting agent *(future)*
An agent that takes raw content (a doc page, Stack Overflow answer, chat transcript) and drafts a structured note for review and import.

---

## Getting started

```bash
# Clone the repo
git clone https://github.com/Dan-Jordan/learn-stack.git
cd learn-stack

# Copy env file and fill in credentials
cp .env.example .env

# Start the database
docker compose up db -d

# Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload

# API docs
# http://localhost:8000/docs
```

---

## Development philosophy

Build in small, working increments. Each phase produces something usable before the next begins.

Avoid over-engineering. If a feature does not help capture or retrieve learning, defer it.
