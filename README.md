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
- Query notes by meaning via `POST /query` — semantic search using vector embeddings
- Ask natural language questions via `POST /ask` — returns a grounded answer with source citations drawn from your own notes
- Draft structured notes from raw pasted content via `POST /draft` — paste a doc, Stack Overflow answer, or any text and get a structured note back for review
- Full CRUD via a FastAPI REST API
- Single-page web UI at `/` — Draft & Save, Notes, Ask, and Semantic Search tabs; no JSON editing required
- Postgres backend with pgvector extension, schema managed by Alembic migrations
- Embeddings generated automatically on note create/update via OpenAI text-embedding API
- Markdown-based note capture workflow for capturing learning before the API is running

---

## Why it exists

Technical learning tends to scatter. Notes live in chat windows, code comments, scratch files, and browser tabs. LearnStack gives that learning somewhere permanent and searchable to live — and is built in a way that reinforces the exact skills the notes are about.

The project serves two purposes simultaneously:

**Practical** — a real tool for capturing and retrieving what you are learning about Python, FastAPI, SQLAlchemy, dbt, Docker, Postgres, and data engineering.

**Educational** — a realistic application for practicing backend development, database modeling, API design, async Python, testing, migrations, RAG, semantic search, and LLM API integration.

---

## Tech stack

| Layer | Tool |
|---|---|
| Python | 3.11+ |
| Backend | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.x (async) |
| Schemas | Pydantic v2 |
| Migrations | Alembic |
| Environment | Docker Compose |
| Testing | pytest + httpx |
| Embeddings | OpenAI text-embedding API + pgvector |
| LLM | Anthropic Claude (Haiku) |
| Web UI | Plain HTML + fetch() (no framework) |

---

## Project phases

### Phase 1 — Basic notes app ✓
Full CRUD on technical notes. Keyword search. Postgres backend. Docker Compose. 10 passing tests.

### Phase 2 — Alembic migrations ✓
Replaced `create_all` on startup with Alembic migration scripts. Schema changes are now versioned and safe. 10 passing tests.

### Phase 3 — pgvector ✓
Added the pgvector Postgres extension and an `embedding` column to the notes table via Alembic migration. Custom Docker image compiles pgvector from source. 10 passing tests.

### Phase 4 — Embedding pipeline ✓
Notes get vector embeddings generated and stored automatically on create/update using the OpenAI text-embedding API (`text-embedding-3-small`, 1536 dimensions). 10 passing tests.

### Phase 5 — Semantic search ✓
`POST /query` takes a natural language question, embeds it, and returns notes ranked by meaning using pgvector cosine similarity. 16 passing tests (6 new).

### Phase 6 — LLM answer generation ✓
`POST /ask` passes retrieved notes + question to Claude. Returns a grounded answer with citations drawn from your own captured knowledge. 21 passing tests (5 new).

### Phase 7 — Note drafting agent ✓
`POST /draft` takes raw pasted content and returns a structured note draft for review. Uses Claude tool use to extract title, content, type, and metadata. Human-in-the-loop: the draft is returned for review, not auto-saved. 27 passing tests (6 new).

### Phase 8 — Web UI ✓
A single-page web UI served by FastAPI at `http://localhost:8000/`. Four tabs: **Draft & Save** (paste raw content → agent structures it → review and save), **Notes** (keyword search, list, expand, delete), **Ask** (RAG-powered question answering with source citations), **Semantic Search** (cosine similarity ranking with score bars). Plain HTML + `fetch()` — no framework, no build step.

---

## Getting started

```bash
# Clone the repo
git clone https://github.com/Dan-Jordan/learn-stack.git
cd learn-stack

# Copy env file and fill in credentials
cp .env.example .env
# Edit .env — set POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, OPENAI_API_KEY, and ANTHROPIC_API_KEY
# OPENAI_API_KEY is required for the embedding pipeline (Phase 4+)
# ANTHROPIC_API_KEY is required for answer generation (POST /ask) and note drafting (POST /draft)

# Start the database (first run builds the custom pgvector image — takes ~1 min)
docker compose up db -d

# Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload

# Web UI
# http://localhost:8000/

# API docs
# http://localhost:8000/docs
```

### Running tests

Tests use a separate database. Run these two commands once after first starting the container:

```bash
docker exec learn-stack-db-1 psql -U postgres -c "CREATE DATABASE learnstack_test;"
docker exec learn-stack-db-1 psql -U postgres -d learnstack_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The `vector` extension must be enabled in the test database separately — it is not inherited from the main database, and the `embedding` column type won't be recognized without it.

These only need to be run once. The databases persist in the Docker volume across restarts. You would need to repeat this after `docker compose down -v` (which destroys volumes).

`TEST_DATABASE_URL` in `.env` must point to this database (already set in `.env.example`).

```bash
pytest
```

---

## Inspiration

This project was inspired by Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept — the idea of a persistent, AI-maintained personal knowledge base where knowledge compounds over time rather than scattering across chat history. The YouTube video [*Build An AI Second Brain Knowledge Base (Step-By-Step)*](https://www.youtube.com/watch?v=yke4fLQUsh4) helped bring that concept into focus.

The architecture here takes a different approach: rather than an LLM-maintained wiki, LearnStack is a RAG system — you write the notes, they get embedded, and the system retrieves and answers from what you actually captured. The implementation is my own, built incrementally over seven phases as a learning exercise in FastAPI, Postgres, pgvector, and LLM API integration.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.