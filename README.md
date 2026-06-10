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
- Two note capture paths: the web UI's Draft & Save tab (browser), or a markdown inbox workflow (`notes-inbox/` → `import_notes.py`) for capturing notes from the terminal/Claude Code without context-switching
- Deployable to Render via `render.yaml` — Docker web service + managed Postgres, one-command setup for cloud hosting

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
| Cloud | Render (web service + managed Postgres) |

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

### Phase 9 — Setup script ✓
`.\setup.ps1` from a clean clone brings the full local stack up in one command: Docker → venv → pip install → `.env` → migrations → test DB → dev server.

### Phase 10 — Cloud deployment ✓
LearnStack runs on [Render](https://render.com) with a managed Postgres database. `render.yaml` defines the web service and database as code. `GET /health` supports Render's health check.

---

## Getting started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and **running** before you run the script
- Python 3.11+

### One-command setup (Windows)

```powershell
git clone https://github.com/Dan-Jordan/learn-stack.git
cd learn-stack
.\setup.ps1
```

The script handles everything in order:

1. Starts the Docker containers (Postgres with pgvector) — Docker Desktop must already be running
2. Creates and activates a Python virtual environment
3. Installs dependencies from `requirements.txt`
4. Copies `.env.example` to `.env` if not already present — then **pauses** and prompts you to fill in your API keys before continuing
5. Runs Alembic migrations against the database
6. Creates the test database (safe to re-run; skips if it already exists)
7. Starts the FastAPI dev server at `http://localhost:8000/`

**First run only:** the Docker build compiles pgvector from source — expect about a minute. Subsequent runs start in seconds.

### API keys required

| Key | Used for |
|---|---|
| `OPENAI_API_KEY` | Embedding pipeline — note create/update, semantic search |
| `ANTHROPIC_API_KEY` | `/ask` (RAG answer generation) and `/draft` (note drafting agent) |

Set both in `.env` before re-running `.\setup.ps1`. The app starts without them but embedding and LLM features will error.

### Running tests

```powershell
pytest
```

The test database is created automatically by `setup.ps1`. If you ever destroy volumes with `docker compose down -v`, re-run `.\setup.ps1` to recreate it.

---

## Cloud deployment (Render)

LearnStack is deployable to [Render](https://render.com) as a Docker web service backed by a managed Postgres instance. `render.yaml` defines everything as code.

### First deploy

1. Push the repo to GitHub.
2. In the Render dashboard: **New → Blueprint** → connect your repo. Render reads `render.yaml` and creates the web service and database automatically.
3. Leave `DATABASE_URL` blank at this step — the database doesn't exist yet. Fill in `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` now.
4. After the blueprint deploys and the database is provisioned, go to the **learnstack** web service → **Environment** tab and set `DATABASE_URL` — copy the **Internal Database URL** from the Render Postgres instance and change the scheme from `postgres://` to `postgresql+asyncpg://`.
5. Save and deploy — Alembic migrations run automatically on startup.
6. The app is live at your Render-assigned URL.

### Subsequent deploys

Push to the connected branch — Render rebuilds and redeploys automatically. Migrations run on every startup and are idempotent — if the schema is already current, they complete instantly with no changes.

### Why migrations run on startup

Shell access is not available on the free tier, so manual migration is not an option. `Dockerfile.app` runs `alembic upgrade head` before starting uvicorn. This is safe because Alembic migrations are idempotent.

### Loading local notes into Render

`pg_dump` and `pg_restore` are not installed locally — Postgres runs inside Docker, so these commands run via `docker exec`.

```powershell
# Dump local database
docker exec -t learn-stack-db-1 pg_dump -U postgres -d learnstack -F c -f /tmp/learnstack_backup.dump
docker cp learn-stack-db-1:/tmp/learnstack_backup.dump ./learnstack_backup.dump
docker exec learn-stack-db-1 rm /tmp/learnstack_backup.dump

# Restore to Render (data only — schema already exists from migrations)
docker cp learnstack_backup.dump learn-stack-db-1:/tmp/learnstack_backup.dump
docker exec -t learn-stack-db-1 pg_restore -d "your-render-external-url" --no-owner --data-only -t notes -F c /tmp/learnstack_backup.dump
docker exec learn-stack-db-1 rm /tmp/learnstack_backup.dump
```

Use the **External Database URL** from the Render dashboard (the internal URL only works from inside Render's network). Use `--data-only -t notes` to skip schema creation and only restore note rows.

---

## Inspiration

This project was inspired by Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept — the idea of a persistent, AI-maintained personal knowledge base where knowledge compounds over time rather than scattering across chat history. The YouTube video [*Build An AI Second Brain Knowledge Base (Step-By-Step)*](https://www.youtube.com/watch?v=yke4fLQUsh4) helped bring that concept into focus.

The architecture here takes a different approach: rather than an LLM-maintained wiki, LearnStack is a RAG system — you write the notes, they get embedded, and the system retrieves and answers from what you actually captured. The implementation is my own, built incrementally over ten phases as a learning exercise in FastAPI, Postgres, pgvector, LLM API integration, and cloud deployment.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.