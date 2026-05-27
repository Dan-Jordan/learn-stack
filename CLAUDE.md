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

**Phase 3 — TBD**

Phases 1 and 2 are complete. Next phase to be determined based on what feels most useful.

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
- [x] FastAPI entry point with lifespan table creation (`app/main.py`)
- [x] Test suite — 10 tests passing (`tests/test_notes.py`)
- [x] `notes-inbox/` note capture workflow and batch import script (`import_notes.py`)

---

## Repository structure

Files marked `[planned]` are specified but not yet created.

```
learnstack/
├── app/
│   ├── main.py              # FastAPI app entry point  [planned]
│   ├── database.py          # SQLAlchemy engine and session
│   ├── models/              # SQLAlchemy ORM models
│   │   └── note.py          # Note ORM model and NoteType enum
│   ├── schemas/             # Pydantic request/response schemas
│   │   └── note.py          # NoteCreate, NoteUpdate, NoteResponse
│   ├── routers/             # FastAPI route handlers  [planned]
│   │   └── notes.py
│   └── crud/                # Database operations (separate from routing)  [planned]
│       └── notes.py
├── tests/                   # [planned]
│   └── test_notes.py
├── notes-inbox/             # Markdown notes awaiting API import
│   └── _template.md
├── import_notes.py          # Batch import script (posts inbox files to API)
├── docker-compose.yml       # PostgreSQL 15 service (no app service yet)
├── Dockerfile               # [planned]
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

## API surface (Phase 1)

| Method | Path | Description |
|---|---|---|
| POST | `/notes` | Create a note |
| GET | `/notes` | List notes (with optional keyword search) |
| GET | `/notes/{id}` | Get a single note |
| PUT | `/notes/{id}` | Update a note |
| DELETE | `/notes/{id}` | Delete a note |

Search is via query param: `GET /notes?q=dbt`

---

## Tech stack

| Layer | Tool | Version |
|---|---|---|
| Backend | FastAPI | latest stable |
| Database | PostgreSQL | 15 |
| ORM | SQLAlchemy | 2.x (use async where possible) |
| Schemas | Pydantic | v2 |
| Environment | Docker Compose | v2 |
| Testing | pytest + httpx | — |
| Python | 3.11+ | — |

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

### Environment
- Never commit secrets or `.env` files
- Provide `.env.example` with all required variable names and placeholder values
- Required variables: `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

---

## Decisions log

Decisions made during development that future work should respect.

| Date | Decision | Reason |
|---|---|---|
| Project start | UUIDs over sequential IDs | Safer for eventual API exposure; avoids enumeration |
| Project start | Pydantic v2 | Current standard; v1 patterns are deprecated |
| Project start | SQLAlchemy 2.x | Modern async support; cleaner query syntax |
| Project start | note_type as enum | Keeps categorization consistent without free-form chaos |
| Project start | tool/project/topic as plain strings in Phase 1 | Defer normalization until usage patterns are clear |
| Project start | No frontend in Phase 1 | Swagger/ReDoc is sufficient; avoid scope creep |
| Project start | Defer tags to Phase 2 | Start with structured fields; add free-form labels after core works |

---

## What is explicitly deferred

Do not build these until the relevant phase is reached:

- Embeddings and vector search (Phase 4)
- Job postings and application tracking (Phase 5)
- AI-assisted learning session workflow (Phase 6)
- Frontend (any phase, as needed)
- Alembic migrations (Phase 2, once schema is stable enough)
- Multi-user support (not planned)
- Cloud deployment (not planned in near term)
- CRM or journaling (out of scope entirely)

---

## Background on the developer

The developer has 19 years of healthcare data experience with an actuarial and modeling background. Python is a growing focus, applied initially for automation. Coursera coursework in Python and pipelines. The goal is to develop backend and data engineering skills that open doors to well-paying roles in health tech and data engineering.

The project is deliberately chosen to build skills that transfer directly to those roles: FastAPI, Postgres, Docker, SQLAlchemy, pytest, and eventually RAG/search.

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
