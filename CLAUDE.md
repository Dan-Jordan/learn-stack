# CLAUDE.md — LearnStack

This file provides context for AI-assisted development on LearnStack. It is the source of truth for project intent, current state, conventions, and decisions made. Update it as the project evolves.

---

## Project identity

**Name:** LearnStack
**Purpose:** A personal technical knowledge system for capturing, organizing, retrieving, and growing technical learning notes.
**Guiding principle:** Start simple. Earn complexity. The system should be useful before it is intelligent.

---

## Vision — what this is building toward

The end state of LearnStack is a **RAG-powered personal knowledge system**: a database of technical notes that you can query in natural language and get answers grounded in your own captured experience.

**How RAG works in this context:**

1. Notes are saved to the database as structured text (Phase 1–2)
2. Notes are split into overlapping chunks — small enough for a model to use as context, large enough to retain meaning (Phase 4)
3. Each chunk is passed through an embedding model, which converts it into a vector — a list of numbers that encodes the chunk's semantic meaning
4. Those vectors are stored alongside the text in Postgres using the `pgvector` extension
5. When a question is asked, the question is also embedded into a vector
6. The system finds the chunks whose vectors are closest to the question vector — i.e. closest in *meaning*, not just keyword match
7. Those chunks are passed to the LLM as context, along with the question
8. The LLM answers using only the retrieved chunks, and cites which notes it drew from

The result: asking "what errors have I hit with SQLAlchemy?" returns an answer built from notes *you* wrote, not a generic response.

**Why this matters for the build order:**

RAG only works if the knowledge base has content worth retrieving. Building the notes system first is not just a learning exercise — it is the prerequisite. Every note saved in Phase 1 is future RAG context.

When working on Phase 1–3, keep the RAG architecture in mind even when not building it yet:
- Store content as raw Markdown — it chunks cleanly
- UUIDs on notes make source citation straightforward
- The `tool`, `topic`, and `project` fields will serve as useful metadata filters at retrieval time (hybrid search: semantic + metadata filter)

---

## Current phase

**Phase 11 — Not started**

Phase 10 is complete. Phase 11 adds HTTP Basic Auth to the Render deployment so the app can be shared without being fully public.

---

## RAG phases overview

| Phase | Focus | Done when |
|---|---|---|
| 3 | pgvector setup | `embedding` column added to notes table via Alembic migration |
| 4 | Embedding pipeline | Notes get vector embeddings generated and stored on create/update |
| 5 | Semantic search | `POST /query` returns notes ranked by meaning, not just keywords |
| 6 | LLM answer generation | A question returns a grounded answer citing your own notes |
| 9 | Setup script | `.\setup.ps1` from a clean clone brings the full stack up in one command |
| 10 | Cloud deployment | LearnStack running on Render at a public URL |
| 11 | Authentication | HTTP Basic Auth gates all routes; credentials set via env vars, changeable without code changes |

**Embedding model:** OpenAI text-embedding API (industry standard, fractions of a cent per note for personal use).

**Deferred to Phase 7 (now complete):** An agent that drafts notes from raw content (paste in a doc or Stack Overflow answer, get a structured note back).

**Deferred to Phase 8:** Job postings — a separate table with structured fields (company, role, status, URL). Not stored in the notes table.

---

## Phase 10 — Complete ✓

**Goal:** LearnStack running on Render with a managed Postgres database and a public URL. ✓

Built:
- [x] `Dockerfile.app` — Python 3.11-slim image for the FastAPI web service (separate from the local-dev Postgres `Dockerfile`)
- [x] `app/routers/health.py` — `GET /health` returns `{"status": "ok"}`; used by Render for health checks
- [x] `app/main.py` — health router registered
- [x] `render.yaml` — Render config-as-code: web service (Docker, `Dockerfile.app`) + managed Postgres instance

**Design decisions:**
- Two Dockerfiles: `Dockerfile` (Postgres + pgvector, local dev only) and `Dockerfile.app` (Python/FastAPI, used by Render) — keeps concerns separate and avoids confusing the Render build
- `render.yaml` marks all three env vars (`DATABASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) as `sync: false` — values are set manually in the Render dashboard, never committed to the repo
- `render.yaml` must specify `plan: free` on the web service — Render defaults to the Starter tier ($7/month) if omitted
- Alembic migration runs automatically on startup via `CMD alembic upgrade head && uvicorn ...` in `Dockerfile.app` — Shell access is not available on the free tier, so manual migration is not possible; Alembic is idempotent so re-running on every deploy is safe
- `Dockerfile.app` uses `python:3.11-slim` (not Alpine) — avoids common compile-time issues with async Postgres drivers (`asyncpg`)
- Health endpoint is deliberately simple — no DB ping, no dependency checks; Render just needs an HTTP 200 to confirm the process started

**Deployment steps (first deploy):**
1. Push repo to GitHub
2. In Render dashboard: New → Blueprint → connect repo → Render reads `render.yaml` and creates the web service and database
3. Set env vars in Render dashboard: `DATABASE_URL` (copy the Internal Database URL from the managed DB's connection string panel, change `postgres://` to `postgresql+asyncpg://`), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
4. Deploy — migrations run automatically on startup
5. App is live at the Render-assigned URL

**Loading local notes into Render (optional):**

`pg_dump` and `pg_restore` are not installed locally — Postgres runs in Docker, so these commands must be run via `docker exec`.

```powershell
# Dump local database
docker exec -t learn-stack-db-1 pg_dump -U postgres -d learnstack -F c -f /tmp/learnstack_backup.dump
docker cp learn-stack-db-1:/tmp/learnstack_backup.dump ./learnstack_backup.dump
docker exec learn-stack-db-1 rm /tmp/learnstack_backup.dump

# Restore to Render (data only — schema already exists from migrations)
docker cp learnstack_backup.dump learn-stack-db-1:/tmp/learnstack_backup.dump
docker exec -t learn-stack-db-1 pg_restore -d "postgresql+asyncpg://..." --no-owner --data-only -t notes -F c /tmp/learnstack_backup.dump
docker exec learn-stack-db-1 rm /tmp/learnstack_backup.dump
```

Use `--data-only -t notes` to skip schema creation and only restore note rows. Any duplicate key errors on a single row can be ignored — they mean that note already exists in Render.

---

## Phase 9 — Complete ✓

**Goal:** A single PowerShell script (`setup.ps1`) that automates the full local dev setup from a clean clone. One command brings the full stack up. ✓

Built:
- [x] `setup.ps1` — 7-step setup: Docker up → venv → pip install → .env copy → Alembic migrations → test DB → uvicorn dev server
- [x] `README.md` — Getting started section rewritten to point to the script

**Design decisions:**
- Script pauses and exits after copying `.env.example` to `.env` on first run — forces the user to fill in API keys before proceeding
- Test database creation is idempotent — `CREATE DATABASE` errors are suppressed if the DB already exists; `CREATE EXTENSION IF NOT EXISTS` is already idempotent
- Postgres readiness is polled with `pg_isready` before running migrations — avoids a race condition on first container start
- The script does not handle macOS/Linux — PowerShell only; a future `setup.sh` is the right approach for cross-platform support
- `Set-StrictMode -Version Latest` and `$ErrorActionPreference = "Stop"` — fail fast on any unexpected error rather than continuing in a broken state

---

## Phase 8 — Complete ✓

**Goal:** A single-page web UI served by FastAPI at `/`. All API capabilities accessible without touching Swagger. ✓

Built:
- [x] `static/index.html` — full single-page UI: Draft & Save, Notes, Ask, Semantic Search tabs
- [x] `app/main.py` — `StaticFiles` mount at `/static`, `GET /` returns `index.html`

**Design decisions:**
- Single HTML file, no framework, no build step — plain HTML + `fetch()` only
- FastAPI serves the file directly via `FileResponse` — no separate server or CDN needed
- Draft flow is two-step by design: `/draft` populates an editable form, user reviews before calling `/notes`
- Notes list lazy-loads on first tab open, not on page load
- Delete requires a `confirm()` dialog — one accidental click should not destroy a note

---

## Phase 7 — Complete ✓

**Goal:** `POST /draft` accepts raw pasted content and returns a structured `NoteCreate` draft for review. The user then saves it manually via `POST /notes`. ✓

Built:
- [x] `app/agent.py` — async Anthropic client, `draft_note(raw_content)` uses Claude tool use with `tool_choice` forced to `create_note`, returns a `NoteCreate`
- [x] `DraftRequest` and `DraftResponse` schemas added to `app/schemas/note.py`
- [x] `app/routers/draft.py` — `POST /draft` endpoint: raw content → agent → draft note
- [x] `app/main.py` — draft router registered
- [x] `tests/test_draft.py` — 6 tests using `AsyncMock` to patch `draft_note`

**Design decisions:**
- No URL support in Phase 7 — paste-only. URL fetching deferred to a later phase.
- No new `NoteType` values added — existing enum covers all current use cases.
- Job postings deferred to Phase 8 with a dedicated table.
- Human-in-the-loop by design: `/draft` returns a draft, does not auto-save. The user reviews before calling `POST /notes`.
- `tool_choice={"type": "tool", "name": "create_note"}` forces structured output — Claude cannot respond in prose.
- `_DRAFT_TOOL` is module-level (not inside the function) — it's a static definition, no reason to recreate it per call.

---

## Phase 6 — Complete ✓

**Goal:** `POST /ask` accepts a question and returns a grounded answer citing the user's own notes. ✓

Built:
- [x] `anthropic>=0.25.0` added to `requirements.txt`
- [x] `ANTHROPIC_API_KEY` added to `.env.example`
- [x] `app/llm.py` — async Anthropic client, `generate_answer(question, context_notes)` builds context from retrieved notes and calls `claude-haiku-4-5-20251001`
- [x] `AskRequest` and `AskResponse` schemas added to `app/schemas/note.py`
- [x] `app/routers/ask.py` — `POST /ask` endpoint: semantic search → LLM → answer + sources
- [x] `app/main.py` — ask router registered
- [x] `tests/test_ask.py` — 5 tests using `AsyncMock` to patch `generate_answer`

**Design decisions:**
- `_client()` is a function (not module-level) so the Anthropic SDK doesn't read `ANTHROPIC_API_KEY` at import time
- Tests mock `generate_answer` because LLM responses are non-deterministic; real API calls are tested for embeddings (deterministic) but not for answers
- `sources` in the response are the notes actually passed as context — caller can see exactly what grounded the answer

---

## Phase 5 — Complete ✓

**Goal:** `POST /query` accepts a question string and returns notes ranked by semantic similarity. ✓

Built:
- [x] `QueryRequest` and `QueryResult` schemas added to `app/schemas/note.py`
- [x] `search_notes_semantic` added to `app/crud/notes.py` — embeds query, runs pgvector cosine distance, filters NULL embeddings, returns `(note, score)` pairs
- [x] `app/routers/query.py` — `POST /query` endpoint, registered in `app/main.py`
- [x] `tests/test_query.py` — 6 tests: empty DB, happy path, score shape, response fields, ranking, limit

**Note:** No vector index added (ivfflat/hnsw). Not needed at personal-note scale. Add via Alembic migration if query performance degrades as the notes database grows.

---

## Phase 4 — Complete ✓

**Goal:** Generate and store vector embeddings for notes automatically on create and update. ✓

Built:
- [x] `openai>=1.0.0` added to `requirements.txt`
- [x] `OPENAI_API_KEY` added to `.env.example`
- [x] `app/embeddings.py` — async helper calling `text-embedding-3-small`, returns 1536 floats
- [x] `app/models/note.py` — `embedding` column added to ORM model using `pgvector.sqlalchemy.Vector(1536)`
- [x] `app/crud/notes.py` — `create_note` embeds on create; `update_note` re-embeds only when `content` changes

---

## Phase 3 — Complete ✓

**Goal:** Add the pgvector Postgres extension and an `embedding` column to the notes table via Alembic migration. No Python application changes yet — just learning how Postgres extensions work and how to add a column to an existing table safely. ✓

Built:
- [x] Switched Docker image to a custom build with pgvector compiled from source (`Dockerfile`)
- [x] `pgvector>=0.3.0` added to `requirements.txt`
- [x] Alembic migration: `CREATE EXTENSION IF NOT EXISTS vector` + `embedding vector(1536)` column (`alembic/versions/7fd0d6c70b7f_add_pgvector_embedding_column.py`)
- [x] Migration applied — pgvector 0.8.0 active, `notes` table has `embedding` column

---

## Phase 2 — Complete ✓

The original Phase 2 scope included new model fields (tags, source, confidence, status) plus Alembic migrations. The extra fields are deferred until the system is in real use and the need is felt. Alembic was the only addition.

**Goal:** Replace the `create_all` on startup approach with Alembic migrations — the standard way real projects manage schema changes safely. ✓

Built:
- [x] Alembic initialized (`alembic.ini`, `alembic/env.py`)
- [x] env.py configured for async engine and model registration
- [x] First migration generated and applied (`alembic/versions/`)
- [x] `create_all` removed from `app/main.py`

**What is explicitly deferred from original Phase 2:**
- tags (Array[String])
- source enum
- confidence enum
- status enum

---

## Phase 1 — Complete ✓

Goal: Build a FastAPI backend with Postgres that supports full CRUD on technical notes, plus basic keyword search.

Done when: A note about `dbt seed` can be created, stored, retrieved by ID, found via keyword search, updated, and deleted — all through the API. ✓

Built:
- [x] PostgreSQL 15 service via Docker Compose (`docker-compose.yml`)
- [x] SQLAlchemy async engine and session (`app/database.py`)
- [x] Note ORM model with all Phase 1 fields (`app/models/note.py`)
- [x] Pydantic schemas: NoteCreate, NoteUpdate, NoteResponse (`app/schemas/note.py`)
- [x] CRUD operations (`app/crud/notes.py`)
- [x] Route handlers (`app/routers/notes.py`)
- [x] FastAPI entry point (`app/main.py`)
- [x] Test suite — 10 tests passing (`tests/test_notes.py`)
- [x] `notes-inbox/` note capture workflow and batch import script (`import_notes.py`)

---

## Repository structure

```
learnstack/
├── app/
│   ├── main.py              # FastAPI app entry point — registers all routers
│   ├── database.py          # SQLAlchemy async engine and session
│   ├── embeddings.py        # OpenAI embedding helper (text-embedding-3-small)
│   ├── llm.py               # Anthropic client — generate_answer() for /ask
│   ├── agent.py             # Anthropic client — draft_note() for /draft
│   ├── models/
│   │   └── note.py          # Note ORM model, NoteType enum, embedding column
│   ├── schemas/
│   │   └── note.py          # All Pydantic schemas: NoteCreate, NoteUpdate, NoteResponse,
│   │                        #   QueryRequest, QueryResult, AskRequest, AskResponse,
│   │                        #   DraftRequest, DraftResponse
│   ├── routers/
│   │   ├── notes.py         # CRUD endpoints
│   │   ├── query.py         # POST /query — semantic search
│   │   ├── ask.py           # POST /ask — RAG answer generation
│   │   ├── draft.py         # POST /draft — notes agent
│   │   └── health.py        # GET /health — health check for Render
│   └── crud/
│       └── notes.py         # Database operations: create, read, update, delete, search
├── tests/
│   ├── conftest.py          # Test database setup and teardown fixture
│   ├── test_notes.py        # 10 tests — CRUD and keyword search
│   ├── test_query.py        # 6 tests — semantic search
│   ├── test_ask.py          # 5 tests — RAG answer endpoint
│   └── test_draft.py        # 6 tests — notes agent endpoint
├── alembic/                 # Migration scripts
│   ├── env.py
│   └── versions/
├── static/
│   └── index.html           # Single-page web UI (Draft & Save, Notes, Ask, Semantic Search)
├── notes-inbox/             # Markdown notes awaiting API import
│   └── _template.md
├── import_notes.py          # Batch import script (posts inbox files to API)
├── setup.ps1                # One-command local dev setup (Windows PowerShell)
├── render.yaml              # Render config-as-code: web service + managed Postgres
├── docker-compose.yml       # PostgreSQL 15 service with pgvector (local dev only)
├── Dockerfile               # Custom pgvector image (pgvector compiled from source, local dev only)
├── Dockerfile.app           # Python/FastAPI image (used by Render for cloud deploy)
├── alembic.ini
├── requirements.txt
├── .env.example
├── README.md
└── CLAUDE.md
```

---

## Data model

### Note (Phase 1 core)

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key, auto-generated |
| title | String | Required |
| content | Text | Required, raw Markdown |
| note_type | Enum | See values below |
| tool | String | Optional (e.g. "dbt", "Docker") |
| project | String | Optional (e.g. "healthcare_claims_dbt") |
| topic | String | Optional (e.g. "CI/CD", "testing") |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**note_type values:** `technical_note`, `command`, `error_fix`, `project_note`, `concept`, `question`

### Phase 2 additions (not yet built)

| Field | Type | Notes |
|---|---|---|
| tags | Array[String] | Free-form labels |
| source | Enum | `personal_experience`, `project`, `llm_explanation`, `documentation`, `course`, `other` |
| confidence | Enum | `verified`, `partially_verified`, `needs_review` |
| status | Enum | `active`, `draft`, `archived`, `needs_follow_up` |

---

## API surface

| Method | Path | Description |
|---|---|---|
| POST | `/notes` | Create a note |
| GET | `/notes` | List notes (with optional keyword search) |
| GET | `/notes/{id}` | Get a single note |
| PUT | `/notes/{id}` | Update a note |
| DELETE | `/notes/{id}` | Delete a note |
| POST | `/query` | Semantic search — returns notes ranked by meaning with scores |
| POST | `/ask` | RAG answer — returns a grounded answer + source notes |
| POST | `/draft` | Notes agent — returns a structured draft note from raw pasted content |
| GET | `/health` | Health check — returns `{"status": "ok"}`; used by Render |

Keyword search via query param: `GET /notes?q=dbt`

---

## Tech stack

| Layer | Tool | Version |
|---|---|---|
| Backend | FastAPI | latest stable |
| Database | PostgreSQL | 15 |
| Vector search | pgvector | 0.8.0 (compiled from source in Docker image) |
| ORM | SQLAlchemy | 2.x (use async where possible) |
| Migrations | Alembic | — |
| Schemas | Pydantic | v2 |
| Environment | Docker Compose | v2 |
| Testing | pytest + httpx | — |
| Python | 3.11+ | — |
| Embeddings | OpenAI text-embedding-3-small | via `openai>=1.0.0` |
| LLM | Anthropic Claude (Haiku) | via `anthropic>=0.25.0` |
| Cloud | Render | Web service + managed Postgres via `render.yaml` |

---

## Conventions

### General
- Use UUIDs as primary keys, not sequential integers
- All datetimes in UTC
- API responses always use Pydantic schemas — never return raw ORM objects
- Keep routing thin: route handlers call crud functions, not database directly
- Separate concerns: `routers/` handles HTTP, `crud/` handles database, `models/` handles ORM, `schemas/` handles validation

### Naming
- Files: `snake_case`
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Environment variables: `UPPER_SNAKE_CASE`
- Database tables: `snake_case`, plural (e.g. `notes`)

### Database
- Use SQLAlchemy 2.x style (not legacy 1.x patterns)
- Define models in `app/models/`
- Use Alembic for migrations once schema stabilizes (Phase 2)
- No raw SQL unless there is a specific reason

### API design
- Return 404 with a clear message when a record is not found
- Return 422 for validation errors (FastAPI handles this automatically via Pydantic)
- Use `response_model` on all route handlers
- Paginate list endpoints: default `limit=20`, max `limit=100`

### Testing
- Use `pytest` with `httpx.AsyncClient` for endpoint tests
- Use a separate test database (set via environment variable)
- At minimum: test create, read, update, delete, and keyword search for notes
- Tests live in `tests/`, mirror the structure of `app/`
- **Review `tests/conftest.py`** to understand how the test database is created empty and torn down between runs — the fixture setup there is the source of truth for test isolation
- **`tests/test_ask.py` and `tests/test_draft.py` use `AsyncMock`** — patch targets the name in the importing module (`app.routers.ask.generate_answer`, `app.routers.draft.draft_note`), not where it's defined. `new_callable=AsyncMock` is required because the router `await`s the function. `mock.assert_called_once()` verifies the layer was invoked exactly once per request.

### Environment
- Never commit secrets or `.env` files
- Provide `.env.example` with all required variable names and placeholder values
- Required variables: `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

---

## Decisions log

Decisions made during development that future work should respect.

| Phase | Decision | Reason |
|---|---|---|
| Project start | UUIDs over sequential IDs | Safer for eventual API exposure; avoids enumeration |
| Project start | Pydantic v2 | Current standard; v1 patterns are deprecated |
| Project start | SQLAlchemy 2.x | Modern async support; cleaner query syntax |
| Project start | note_type as enum | Keeps categorization consistent without free-form chaos |
| Project start | tool/project/topic as plain strings | Defer normalization until usage patterns are clear |
| Project start | No frontend (overturned in Phase 8) | Swagger/ReDoc was sufficient early on; single-page UI added in Phase 8 once core API was stable |
| Project start | Defer tags, source, confidence, status fields | Start with structured fields; add after core works and usage patterns emerge |
| Phase 2 | All schema changes via Alembic migrations | Replaces `create_all` on startup; standard safe approach for production schema evolution |
| Phase 3 | pgvector enabled via migration, not app startup | Keeps extension management with schema management; idempotent with `IF NOT EXISTS` |
| Phase 3 | Custom Docker image with pgvector compiled from source | Official Postgres image doesn't include pgvector; custom Dockerfile gives full control |
| Phase 4 | OpenAI `text-embedding-3-small` for embeddings | Industry standard; cheap at personal scale; 1536-dimension vectors |
| Phase 4 | Re-embed only when `content` changes on update | Title/metadata edits don't change meaning; avoids unnecessary API calls |
| Phase 4 | Embeddings generated at write time, not in batch | Keeps notes immediately searchable after create/update; acceptable latency at personal scale |
| Phase 5 | No pgvector index (ivfflat/hnsw) | Not needed at personal-note scale; add via migration if query performance degrades |
| Phase 5 | Cosine distance for similarity ranking | Standard for normalized text embeddings; pgvector supports it natively |
| Phase 6 | `_client()` is a lazy function, not module-level | Prevents SDK from reading API keys at import time; applies to `llm.py`, `agent.py`, and `embeddings.py` |
| Phase 6 | LLM tests mock `generate_answer`, not real API calls | LLM responses are non-deterministic; mocking keeps tests fast and reliable |
| Phase 6 | `sources` in `/ask` response = notes passed as context | Caller sees exactly what grounded the answer, not just what was retrieved |
| Phase 7 | `tool_choice` forced to `create_note` in draft agent | Ensures structured output — Claude cannot respond in prose |
| Phase 7 | `/draft` returns a draft, does not auto-save | Human-in-the-loop by design; keeps junk out of the RAG knowledge base |
| Phase 7 | No URL support in draft agent | Paste-only keeps scope tight; URL fetching adds meaningful complexity |
| Phase 7 | Job postings deferred to a future phase with dedicated table | Forcing them into the notes table loses structure; need company, role, status, URL fields — deferred indefinitely |
| Phase 8 | Single HTML file, no JS framework | Keeps scope minimal; `fetch()` is sufficient for a personal tool at this scale |
| Phase 8 | FastAPI serves the UI directly via `FileResponse` | No separate server, no new infrastructure — consistent with "start simple" principle |
| Phase 8 | Notes list lazy-loads on first tab open | Avoids a network call on every page load; most sessions start on the Draft tab |
| Phase 9 | Script pauses after copying `.env` on first run | Forces user to fill in API keys before migrations run — prevents silent failures |
| Phase 9 | `pg_isready` poll before running migrations | First container start takes a few seconds; running migrations immediately causes a connection error |
| Phase 9 | Test DB creation is idempotent — errors suppressed | Safe to re-run `setup.ps1` at any time without manual cleanup |
| Phase 9 | PowerShell only (`setup.ps1`) | Matches the target platform (Windows); a `setup.sh` is the right future addition for macOS/Linux |
| Phase 10 | Two Dockerfiles (`Dockerfile` and `Dockerfile.app`) | `Dockerfile` builds the Postgres+pgvector image for local dev; `Dockerfile.app` builds the Python/FastAPI image for Render — mixing them would require runtime branching |
| Phase 10 | Alembic migration wired into Docker startup command | Free tier has no shell access; `alembic upgrade head && uvicorn ...` in CMD runs migrations automatically; idempotent so safe on every deploy |
| Phase 10 | `plan: free` required in `render.yaml` | Render defaults to Starter ($7/month) if plan is omitted; must be explicit |
| Phase 10 | `sync: false` on all env vars in `render.yaml` | API keys and DB connection strings must never be committed; Render dashboard is the right place to set them |
| Phase 10 | `python:3.11-slim` not Alpine for `Dockerfile.app` | Alpine requires extra musl/gcc steps to compile `asyncpg`; slim avoids that without adding significant image size |
| Phase 10 | Health endpoint has no DB ping | Render's health check just needs a 200; adding DB ping means a DB outage restarts the web service unnecessarily |

---

## What is explicitly deferred

Do not build these until the relevant phase is reached:

- Authentication (Phase 11) — HTTP Basic Auth gating all routes; credentials via env vars
- Job postings and application tracking — separate table with dedicated fields; not stored in notes; no target phase
- URL fetching in the draft agent — paste-only for now; defer to a later phase
- Multi-user support (not planned)
- CRM or journaling (out of scope entirely)

---

## Follow-ups

Items to revisit at no fixed deadline. Not deferred features — these are code quality, consistency, and design questions worth returning to when the system is in regular use.

| Area | Item | Notes |
|---|---|---|
| `app/agent.py`, `app/llm.py`, `app/embeddings.py` | New API client created on every call | All three use `_client()` to defer SDK initialization. A lazy-init module-level singleton would satisfy both concerns (deferred init + reuse). Low priority at current scale. |
| `app/crud/notes.py` | No pgvector index (ivfflat/hnsw) on the `embedding` column | Not needed at personal-note scale. Add via Alembic migration if semantic search slows as the notes table grows. |
| `app/models/note.py` | Phase 2 schema fields still unbuilt — tags, source, confidence, status | Deferred until usage patterns are clear. Revisit after the system has been in real use for a while. Requires Alembic migration + schema + CRUD updates. |
| `app/agent.py` | URL fetching in the draft agent | `/draft` is paste-only. Future: accept a URL, fetch the content server-side, pass to the agent. Adds meaningful complexity — defer until paste workflow is well-exercised. |

---

## Background on the developer

The developer has 19 years of healthcare data experience with an actuarial and modeling background. Python is a growing focus, applied initially for automation. Coursera coursework in Python and pipelines. The goal is to develop backend and data engineering skills that open doors to roles in health tech and data engineering that align with his background and trajectory.

The project is deliberately chosen to build skills that transfer directly to those roles: FastAPI, Postgres, Docker, SQLAlchemy, Alembic, pytest, pgvector, LLM API integration (OpenAI, Anthropic), and RAG/semantic search.

Prefer explanations that connect new concepts to the developer's existing strengths in data modeling, logic, and analytical thinking. Avoid over-scaffolding; this developer learns well by doing.

---

## Note capture workflow

While the API is being built, notes are written as markdown files and batch-imported later.

**To create a note:** tell Claude Code "create a note about X". It will write a new file to `notes-inbox/` using `notes-inbox/_template.md` as the format and `notes-inbox/sqlalchemy-session-unit-of-work.md` as a filled-in example.

**To import notes:** once the API is running, `python import_notes.py` posts all inbox files to the API and moves them to `notes-inbox/processed/`.

---

## Implementation workflow

Before changing code, create a short implementation plan that includes:
- Files expected to be edited
- Risks or gotchas
- Tests to run after the change

After implementation, summarize the diff and explain how to validate the change works.

---

## How to use this file

When working on LearnStack with AI assistance:

1. Reference this file at the start of a session to orient the assistant
2. Ask the assistant to update this file when decisions are made or the phase changes
3. Keep the decisions log current — it prevents relitigating settled questions
4. If a proposed feature is not in the current phase, check the deferred list before building it

The file should stay honest about current state. When Phase 1 is complete, update the **Current phase** section before starting Phase 2.
