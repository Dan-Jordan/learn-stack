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
2. Each note is passed through an embedding model, which converts it into a vector — a list of numbers that encodes the note's semantic meaning (Phase 4)
3. Those vectors are stored alongside the text in Postgres using the `pgvector` extension
4. When a question is asked, the question is also embedded into a vector
5. The system finds the notes whose vectors are closest to the question vector — i.e. closest in *meaning*, not just keyword match
6. Those notes are passed to the LLM as context, along with the question
7. The LLM answers using only the retrieved notes, and cites which ones it drew from

(Notes are currently embedded *whole* — one vector per note. Splitting long notes into overlapping chunks is a possible future refinement; see Follow-ups.)

The result: asking "what errors have I hit with SQLAlchemy?" returns an answer built from notes *you* wrote, not a generic response.

**Why this matters for the build order:**

RAG only works if the knowledge base has content worth retrieving. Building the notes system first is not just a learning exercise — it is the prerequisite. Every note saved in Phase 1 is future RAG context.

When working on Phase 1–3, keep the RAG architecture in mind even when not building it yet:
- Store content as raw Markdown — it chunks cleanly if per-note chunking is added later (see Follow-ups)
- UUIDs on notes make source citation straightforward
- The `tool`, `topic`, and `project` fields will serve as useful metadata filters at retrieval time (hybrid search: semantic + metadata filter)

---

## Current phase

**Phase 16 — Complete ✓**

Phase 16 gates every route in the deployed app behind HTTP Basic Auth — a single hardcoded username/password pair via `BASIC_AUTH_USERNAME`/`BASIC_AUTH_PASSWORD` env vars — so the app can be shared without being fully public. Every route is gated except `GET /health` (Render's health check can't supply credentials); `/docs`, `/redoc`, and `/openapi.json` are gated too (disabled by default, re-added behind auth) so the API schema itself isn't publicly browsable. The web UI needs no JS changes — the browser's native Basic Auth prompt handles it. This was split off from what CLAUDE.md originally planned as one bundled "Authentication + remote MCP" phase — see `docs/phases/phase-16.md` for the split rationale.

Phase 15 (local stdio MCP server) is complete — see `docs/phases/phase-15.md`. Phase 14 (Neon database migration) is complete — production Postgres now lives on Neon, with the web service still on Render. See `docs/phases/phase-14.md`.

**Future phases are unnumbered.** Completed phases keep their numbers as a historical record; upcoming work is listed in order *without* numbers, so phases can be reordered or inserted without renumbering everything downstream. The future phases below are in intended order.

**Future phase — Remote MCP (next up).** The MCP server (Phase 15's stdio path) is exposed remotely over HTTP with OAuth 2.1 + PKCE, so claude.ai's web/mobile chat apps and Claude Desktop's own Connectors (not just Claude Code) can reach it. Originally bundled with HTTP Basic Auth as one "Authentication + remote MCP" phase; split out (Phase 16) once research showed the OAuth/remote-transport half is a substantially larger, separate build — the `mcp` SDK ships a complete OAuth 2.1 authorization server (PKCE, Dynamic Client Registration all built in), but the storage backend (an `OAuthAuthorizationServerProvider` implementation over new DB tables for clients/auth-codes/tokens) plus Streamable HTTP transport wiring still has to be hand-built. Client registration will use a **static Client ID/Secret**, not Dynamic Client Registration — confirmed during Phase 16's planning: this is a single personal user with exactly one client that will ever connect (all of claude.ai's surfaces share one registration server-side). No standalone section yet — a full plan will be written when it comes up.

**Future phase — Insights.** A scheduled clustering pipeline over note embeddings. See the Insights section below.

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
| 11 | Notes Assistant | `POST /chat` runs a multi-tool agent that decides whether to search notes, draft one, or just reply |
| 12 | Continuous integration | GitHub Actions runs the test suite on every PR; a branch-protection rule gates merges to `main` |
| 13 | Logging | Leveled logging across the app's boundaries and error paths; `LOG_LEVEL`-configurable and observable on Render |
| 14 | Neon database migration | Production Postgres moved from Render's expiring free tier to Neon; web service stays on Render |
| 15 | MCP server | Local stdio MCP server exposes `search_notes` + `create_note` (staged via `pending_notes`, reviewed in a "Pending" tab); notes land in Neon |
| 16 | HTTP Basic Auth | Every route except `/health` requires HTTP Basic Auth (env-var credentials); fails closed if unset |
| — | Remote MCP | The MCP server is exposed remotely over HTTP with OAuth 2.1 + PKCE, reachable from claude.ai web/mobile/Desktop Connectors |
| — | Insights | A scheduled job clusters note embeddings into topics and labels them; `/insights` shows the results |

**Embedding model:** OpenAI text-embedding API (industry standard, fractions of a cent per note for personal use).

**Deferred to Phase 7 (now complete):** An agent that drafts notes from raw content (paste in a doc or Stack Overflow answer, get a structured note back).

**Deferred to Phase 8:** Job postings — a separate table with structured fields (company, role, status, URL). Not stored in the notes table.

---

## Completed phase archives

Full narratives for completed phases (Goal / Why / Built / Verified / design-decision
prose / gotchas) are archived **verbatim**, one file per phase, in `docs/phases/`.
The durable, compressed record stays in this file — the Decisions log, the
Risks/gotchas carried into Follow-ups, the RAG phases overview table, and the
Conventions section. Consult an archive when working on something that phase built.

- [Phase 1 — Notes CRUD API](docs/phases/phase-1.md) — FastAPI + Postgres CRUD, keyword search, notes-inbox import workflow
- [Phase 2 — Alembic migrations](docs/phases/phase-2.md) — `create_all` on startup replaced with Alembic migrations
- [Phase 3 — pgvector setup](docs/phases/phase-3.md) — pgvector extension + `embedding` column (custom Docker image)
- [Phase 4 — Embedding pipeline](docs/phases/phase-4.md) — embeddings generated on note create/update (`text-embedding-3-small`)
- [Phase 5 — Semantic search](docs/phases/phase-5.md) — `POST /query` — cosine-similarity semantic search
- [Phase 6 — LLM answer generation](docs/phases/phase-6.md) — `POST /ask` — grounded answers citing your own notes
- [Phase 7 — Draft agent](docs/phases/phase-7.md) — `POST /draft` — structures raw pasted content into a note (forced tool use)
- [Phase 8 — Web UI](docs/phases/phase-8.md) — single-page web UI served at `/` (no framework, no build step)
- [Phase 9 — Setup script](docs/phases/phase-9.md) — `setup.ps1` — one-command local setup from a clean clone
- [Phase 10 — Cloud deployment (Render)](docs/phases/phase-10.md) — Render deploy: two Dockerfiles, `render.yaml`, migrations on startup
- [Phase 11 — Notes Assistant (/chat agent loop)](docs/phases/phase-11.md) — `POST /chat` multi-tool agent loop; confirm-before-save `create_note`
- [Phase 12 — Continuous integration](docs/phases/phase-12.md) — GitHub Actions test gate, suite-wide embedding mock, branch protection
- [Phase 13 — Logging](docs/phases/phase-13.md) — leveled logging conventions, `LOG_LEVEL`, never-log-values rule
- [Phase 14 — Neon database migration](docs/phases/phase-14.md) — production Postgres moved to Neon; `split_ssl_args`, `pool_pre_ping`, deploy-order gotchas
- [Phase 15 — Local stdio MCP server](docs/phases/phase-15.md) — stdio MCP server (`search_notes` + staged `create_note`), pending review gate, **MCP host wiring**
- [Phase 16 — HTTP Basic Auth](docs/phases/phase-16.md) — HTTP Basic Auth on every route except `/health`; fail-closed; gated `/docs`

---

## Future phase — Insights

**Goal:** A scheduled job clusters note embeddings into topics, labels each cluster via the LLM, and stores the results so the UI can show what your notes are actually about — without asking a question.

**Why:** Embeddings are generated on every note (Phase 4) but are currently only used reactively, in `/query` and `/ask`. This phase mines that existing data for patterns, and introduces a scheduled/batch pipeline pattern (a core data engineering skill) at a scale that fits "start simple."

Planned components:
- [ ] `app/clustering.py` — `cluster_notes()`: pulls all notes with non-null embeddings, runs `sklearn.cluster.KMeans` (or `MiniBatchKMeans`) to group them, then sends each cluster's note titles/snippets to Claude Haiku to generate a short label
- [ ] Alembic migration — add nullable `cluster_id` FK column to `notes`, plus a new `note_clusters` table (`id`, `label`, `created_at`)
- [ ] `app/routers/insights.py` — `GET /insights` returns clusters with labels and member notes; `POST /insights/refresh` manually triggers `cluster_notes()`
- [ ] `app/main.py` — register insights router; wire up `APScheduler` to run `cluster_notes()` on a weekly interval
- [ ] `static/index.html` — new "Insights" tab: cluster cards (label, note count, member titles linking to notes), plus a "Refresh now" button
- [ ] `tests/test_clustering.py` — unit test `cluster_notes()` against a fixture set of pre-made embeddings; mock the LLM labeling call (same pattern as `test_ask.py`)
- [ ] `tests/test_insights.py` — endpoint tests for `/insights` and `/insights/refresh`, mocking `cluster_notes`

**Design decisions (proposed):**
- Recompute clusters wholesale on each run rather than incrementally — simpler, and cheap at personal-note volume
- `cluster_id` lives directly on `notes` (one cluster per note at a time) rather than a join table — avoids unnecessary many-to-many complexity
- `APScheduler` runs in-process inside the FastAPI app — no new infrastructure, consistent with "start simple"; revisit if Render's free tier sleeps the process and breaks the schedule
- K (number of clusters) starts as a fixed small number; revisit once there's enough notes for tuning to matter

**Risks / gotchas:**
- Clustering is only meaningful once there are enough notes (roughly 20+) with embeddings
- Choosing K is a manual/iterative judgment call — bad K gives meaningless clusters
- LLM labeling adds a small API cost per cluster per run
- Render free-tier process sleep could cause the in-process scheduler to miss runs — needs verification once deployed

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
│   ├── assistant.py         # Anthropic client — run_assistant() agent loop for /chat
│   ├── mcp_server.py        # Local stdio MCP server (low-level mcp.server.Server) — search_notes + create_note (staged)
│   ├── prompts.py           # Shared tool prose: SEARCH_NOTES_TOOL, CREATE_NOTE_TRIGGER, NOTE_QUALITY_GUIDANCE
│   ├── auth.py              # get_current_user() — HTTP Basic Auth dependency, gates all routes except /health
│   ├── models/
│   │   └── note.py          # Note + PendingNote ORM models, NoteType enum, embedding column
│   ├── schemas/
│   │   └── note.py          # All Pydantic schemas: NoteCreate, NoteUpdate, NoteResponse,
│   │                        #   QueryRequest, QueryResult, AskRequest, AskResponse,
│   │                        #   DraftRequest, DraftResponse, ChatRequest, ChatResponse,
│   │                        #   ToolCall, ChatMessage; plus NOTE_TOOL_INPUT_SCHEMA (data contract)
│   ├── routers/
│   │   ├── notes.py         # CRUD endpoints
│   │   ├── query.py         # POST /query — semantic search
│   │   ├── ask.py           # POST /ask — RAG answer generation
│   │   ├── draft.py         # POST /draft — notes agent
│   │   ├── assistant.py     # POST /chat — multi-tool notes assistant
│   │   ├── pending.py       # /pending — list/edit/approve/reject MCP-staged notes
│   │   └── health.py        # GET /health — health check for Render
│   └── crud/
│       ├── notes.py         # Database operations: create, read, update, delete, search
│       └── pending.py       # Staged-note ops: create/list/update/approve (→ create_note)/reject
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions: pytest on every PR/push against pgvector service container
├── tests/
│   ├── conftest.py          # Shared engine + client + db_session fixtures; autouse embedding mock (no API key)
│   ├── test_notes.py        # 10 tests — CRUD and keyword search
│   ├── test_query.py        # 6 tests — semantic search
│   ├── test_ask.py          # 5 tests — RAG answer endpoint
│   ├── test_draft.py        # 6 tests — notes agent endpoint
│   ├── test_assistant.py    # 7 tests — notes assistant agent loop
│   ├── test_pending.py      # 8 tests — pending CRUD + endpoints (approve promotes & embeds)
│   ├── test_mcp.py          # 6 tests — MCP tool discovery + dispatch (search + staged create)
│   └── test_auth.py         # 6 tests — HTTP Basic Auth: no/wrong/correct creds, /health public, docs gated
├── alembic/                 # Migration scripts
│   ├── env.py
│   └── versions/
├── docs/
│   └── phases/             # Archived completed-phase narratives (moved verbatim from CLAUDE.md)
├── .claude/
│   └── commands/
│       └── wrap-phase.md    # /wrap-phase — end-of-phase docs/archive/commit/PR checklist
├── static/
│   └── index.html           # Single-page web UI (Draft & Save, Notes, Pending, Ask, Assistant, Semantic Search)
├── notes-inbox/             # Markdown notes awaiting API import
│   └── _template.md
├── import_notes.py          # Batch import script (posts inbox files to API)
├── setup.ps1                # One-command local dev setup (Windows PowerShell)
├── render.yaml              # Render config-as-code: web service only (DB hosted on Neon)
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

### PendingNote (Phase 15 — staged MCP writes)

A separate table holding notes captured via the MCP `create_note` tool, awaiting human review before promotion into `notes`. Mirrors only the writable `NoteCreate` fields — **no `embedding` column** (embedding happens once, at approval, on the final text) and **no `updated_at`** (edits are cheap text `UPDATE`s and the row is short-lived). Kept separate from `notes` so every `notes` row stays a real, approved, embedded note and no read path needs to know "pending" exists. Model: `PendingNote` in `app/models/note.py`; table created by migration `daf904df7559`.

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key, auto-generated |
| title | String | Required |
| content | Text | Required, raw Markdown |
| note_type | Enum | Reuses the same `notetype` enum as `notes` |
| tool | String | Optional |
| project | String | Optional |
| topic | String | Optional |
| created_at | DateTime | Auto-set |

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
| POST | `/chat` | Notes assistant — multi-tool agent loop; decides whether to search, draft, or reply; returns the reply plus a tool-call trace |
| GET | `/pending` | List MCP-staged notes awaiting review |
| PUT | `/pending/{id}` | Edit a staged note in place (partial update) |
| POST | `/pending/{id}/approve` | Promote a staged note into `notes` (embeds the final text); returns the created note |
| DELETE | `/pending/{id}` | Reject and discard a staged note |
| GET | `/health` | Health check — returns `{"status": "ok"}`; used by Render |

Every route above except `GET /health` requires HTTP Basic Auth (Phase 16), as do `/`, `/docs`, `/redoc`, and `/openapi.json`.

Keyword search via query param: `GET /notes?q=dbt`

---

## Tech stack

| Layer | Tool | Version |
|---|---|---|
| Backend | FastAPI | latest stable |
| Database | PostgreSQL | 15 local (Docker) / 18 prod (Neon) |
| Vector search | pgvector | 0.8.0 local (compiled in Docker image) / 0.8.1 prod (Neon) |
| ORM | SQLAlchemy | 2.x (use async where possible) |
| Migrations | Alembic | — |
| Schemas | Pydantic | v2 |
| Environment | Docker Compose | v2 |
| Testing | pytest + httpx | — |
| Python | 3.11+ | — |
| Embeddings | OpenAI text-embedding-3-small | via `openai>=1.0.0` |
| LLM | Anthropic Claude (Haiku 4.5) | via `anthropic>=0.25.0` |
| MCP | Model Context Protocol SDK | `mcp>=1.28.0` — local stdio server (`app/mcp_server.py`) on the low-level `mcp.server.Server` |
| Web UI | Plain HTML + `fetch()` | no framework, no build step (`static/index.html`) |
| Cloud | Render + Neon | Render runs the web service (`render.yaml`); Neon hosts the Postgres database (`DATABASE_URL` secret) |
| Auth | HTTP Basic Auth | FastAPI `HTTPBasic`, gates all routes except `/health` (`BASIC_AUTH_USERNAME`/`PASSWORD` secrets) |

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
- **`tests/test_assistant.py` mocks one level deeper** — it patches `app.assistant._client` (not `run_assistant`) so the *real* agent loop runs, feeding scripted tool-use/text responses via `messages.create`'s `side_effect`. `app.assistant.notes_crud.search_notes_semantic` is also mocked to avoid real DB/embedding calls. This exercises tool dispatch, loop termination, and the `MAX_ITERATIONS` cap. The cap test supplies exactly `MAX_ITERATIONS` scripted responses, so a runaway loop would raise `StopAsyncIteration` — the test passing is itself proof the cap holds.
- **Embeddings are mocked suite-wide by an autouse fixture (`mock_embeddings` in `conftest.py`)** — it patches `app.crud.notes.embed_text`, the single seam both the note-write and semantic-query paths use, with a deterministic content-derived stub. This is what lets the whole suite (and CI) run with **no `OPENAI_API_KEY`** and make no live calls — every test runs on every PR, no skips. A test that needs *specific* embedding values (e.g. `test_semantic_query_ranking`) patches `app.crud.notes.embed_text` again inside the test with controlled vectors; the inner patch wins while active. Note: tests do **not** make live API calls — don't add a `skipif`-on-key test, since pytest doesn't load `.env` and it would silently never run. A genuine live smoke check belongs in a separate scheduled workflow with a secret, not in this suite.
- **`conftest.py` exposes `engine`, `client`, and `db_session` (Phase 15)** — the engine is one fixture, shared so `client` (the ASGI test client, `get_db` overridden) and `db_session` (a plain session) hit the *same* database. `test_pending.py` uses `db_session` + `crud.pending.create_pending` to seed pending rows because there is **no HTTP create path** for them, then asserts through `client`. `test_mcp.py` calls the low-level server's `list_tools`/`call_tool` directly (the decorators leave them as plain coroutine functions), mocking `AsyncSessionLocal` and the `crud` functions — it tests *dispatch*, not the DB.

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
| Phase 11 | `/chat` omits `tool_choice` (defaults to `auto`) | The model decides per turn whether to search, draft, or reply — the defining difference from `/draft`'s forced single tool, and what makes it an agent |
| Phase 11 | `create_note` is confirm-before-save (human-in-the-loop) | Agent records the proposed draft in the response trace but never persists; user reviews and saves via `POST /notes`. Keeps junk out of the RAG store, consistent with `/draft` |
| Phase 11 | Assistant loop backed by Claude Haiku 4.5 | Matches `/draft` and `/ask`; cheapest model, sufficient for a 2-tool loop at personal scale |
| Phase 11 | Hard cap of 5 loop iterations (`MAX_ITERATIONS`) | Prevents runaway looping; on cap, return the current text flagged with the limit |
| Phase 11 | `create_note` tool input schema extracted to one shared `NOTE_TOOL_INPUT_SCHEMA` | Single source of truth for the tool contract in `app/schemas/note.py`; `agent.py` and `assistant.py` both reference it so the note shape can't drift (mirrors `NoteCreate`) |
| Phase 11 | Trigger conditions go on the tool `description`; note-quality policy goes in the `system` prompt | Trigger / when-to-call is tool-intrinsic (and only matters under `auto`); editorial policy is task-level. DRY applies to contracts, not to prompt prose tuned per surface |
| Phase 11 | `/chat` request uses client-supplied `history`, not `conversation_id` | Multi-turn works statelessly now (like `/ask`); a `conversation_id` is a no-op without server-side conversation storage, which stays deferred. History is text-only — tool context isn't replayed across turns |
| Phase 11 | Agent-loop tests mock `app.assistant._client`, not `run_assistant` | Exercises the real loop (dispatch, termination, cap); mocking the helper would test nothing. The `_client()` indirection is the test seam |
| Phase 12 | CI mocks the embedding call instead of using a real `OPENAI_API_KEY` | A merge gate must be deterministic and self-contained; live model calls flake on drift/network/rate limits and train you to ignore red. CI tests your code, not OpenAI's model — and no secret keeps the key out of CI, consistent with `render.yaml`'s `sync: false` |
| Phase 12 | One autouse fixture patches the single `embed_text` seam | Both the note-write and semantic-query paths funnel through `app.crud.notes.embed_text`, so one patch removes every live call. The stub is content-derived with non-negative components, keeping similarity scores in the `[0, 1]` range tests assert |
| Phase 12 | Ranking test uses controlled vectors, not the real API | Tests LearnStack's ordering/scoring code (deterministic, yours) rather than OpenAI's semantic quality (not yours). Runs in CI on every PR with no key — avoids a `skipif`-gated live test that silently never runs (pytest doesn't load `.env`). Live smoke checks, if ever wanted, belong in a separate scheduled workflow, not the gate |
| Phase 12 | Prebuilt `pgvector/pgvector:pg15` service container; `create_all` (not Alembic) in CI | Avoids compiling pgvector from source like the local `Dockerfile`. `conftest.py` builds the schema from ORM models, so CI only needs the `vector` extension present — no migration step for the test run |
| Phase 12 | Branch protection via ruleset: require the `test` check; require PR with **0 approvals**; keep admin bypass | On a solo repo, ≥1 required approval permanently blocks merges (you can't approve your own PR); 0 approvals still forces changes through the gated PR. Admin bypass left on so a misconfigured rule can't lock you out of your own repo |
| Phase 13 | `LOG_LEVEL` parsed with `getattr(logging, LOG_LEVEL.upper(), logging.INFO)` | A typo in the env var falls back to INFO instead of crashing on startup; a startup crash on Render is worse than a wrong level |
| Phase 13 | `LOG_LEVEL` committed as `value: INFO` in `render.yaml`, not `sync: false` | It isn't a secret, so the default belongs in version control where it's visible and tracked; changing verbosity is a deliberate edit-and-redeploy. Trade-off: no dashboard-only flip without a deploy |
| Phase 13 | `logger.error` + re-raise vs `logger.exception` when swallowing | The deciding factor is whether the exception keeps propagating. Re-raise → `logger.error` with no `exc_info` (whoever finally handles it logs the traceback — avoids duplicate tracebacks); swallow here → `logger.exception` (the only place the traceback gets captured) |
| Phase 13 | `embed_text`'s ERROR wrap adds context (input size), not visibility | The failure is logged with a traceback either way (uvicorn or the `/chat` loop). The wrap carries `len(text)`, which the traceback lacks and which distinguishes a token-limit failure from a transient one; its DEBUG breadcrumb is invisible in prod, so it's also the only embedding-specific signal at the prod level |
| Phase 13 | Never log values — only ids, field names, sizes, counts | API keys, embedding vectors, raw note content, and question text are never logged; leaking secrets/PII to logs is a real production failure mode |
| Phase 13 | Routers deliberately left unlogged | Their only error paths are `404`s — expected client outcomes already in uvicorn's access log; 500s already get a traceback upstream. Request logging would duplicate uvicorn and be cargo-cult |
| Phase 14 | Move only the database to Neon; keep the web service on Render | The web service free tier isn't expiring — the database is. Smallest change that fixes the actual problem; no application logic moves |
| Phase 14 | Strip both `sslmode` *and* `channel_binding`; pass SSL via `connect_args={"ssl": True}` | asyncpg configures TLS through the driver, not libpq URL params, and rejects both libpq params Neon's string carries. Done generically in `split_ssl_args` (shared by the app and migration engines) so the local (no-param) URL is a no-op — local/tests/CI untouched |
| Phase 14 | Use Neon's direct (non-pooler) endpoint | The `-pooler` (PgBouncer transaction-mode) host breaks asyncpg's prepared statements; the direct host avoids it with no `statement_cache_size=0` workaround for pooling a single low-traffic app doesn't need |
| Phase 14 | Decline Neon Auth / `neonctl` AI tooling; create a plain Postgres project | Neon Auth is multi-user identity (not planned; the upcoming Authentication phase is single-user Basic Auth) and would couple the app to a Neon product — against this phase's goal of staying DB-agnostic so the next move stays cheap |
| Phase 14 | Save Neon `DATABASE_URL` in Render with "Save only"; let the merge-triggered deploy apply it | The deployed app still runs pre-fix code; pointing it at Neon before the SSL fix is on `main` would crash-loop on `sslmode`. Saving without deploying stages the secret so the auto-deploy picks it up with the fix in place |
| Phase 14 | Share `split_ssl_args()` between `app/database.py` and `alembic/env.py` | `env.py` builds its own engine straight from `DATABASE_URL`, so the original app-only SSL fix didn't cover the startup migration — `alembic upgrade head` crashed on `sslmode` on the first real deploy. One shared helper means both connection paths strip the params identically and can't drift. Local-only verification missed this because the local URL has no `sslmode` to trip on |
| Phase 14 | `pool_pre_ping=True` on the app engine | Neon autosuspends on idle and drops its side of pooled connections; without a liveness check the first request after idle grabs a dead connection and errors (red on the Notes tab, recovers on refresh). pre_ping discards dead connections transparently. Only the app engine pools — `alembic/env.py` uses `NullPool`, so it doesn't need it. Fixes the *error*, not the cold-start *latency*, which is inherent |
| Phase 15 | Shared tool *prose* lives in `app/prompts.py`; the schema stays in `schemas/note.py` | Model-steering prose (tool descriptions, quality policy, trigger) is a different concern from Pydantic validation. `NOTE_TOOL_INPUT_SCHEMA` stays beside `NoteCreate` because it mirrors that model (drift visible when adjacent); `prompts.py` imports nothing from `note.py`, so no cycle. A `create_note` tool def is composed at each consumer from prose + schema |
| Phase 15 | MCP server on low-level `mcp.server.Server`, not FastMCP | FastMCP generates a tool's schema *from* a typed function and can't consume a pre-built dict. `NOTE_TOOL_INPUT_SCHEMA` already exists as data shared with the Anthropic tools in `/chat` and `/draft`, so the contract must stay a dict with one source of truth. Low-level `Server` takes the dict directly (`types.Tool(inputSchema=…)`); FastMCP would force a second definition and reintroduce drift. Also exposes MCP's discovery/dispatch mechanics, mirroring the `/chat` loop |
| Phase 15 | Reuse the shared schema *value*, re-keyed per API | `SEARCH_NOTES_TOOL`/`NOTE_TOOL_INPUT_SCHEMA` key the JSON schema under `input_schema` (Anthropic Messages API spelling); MCP's `types.Tool` spells it `inputSchema`. The shared artifact is the schema *value* (+ name + description); each surface supplies its own wrapper key. One contract, two spellings |
| Phase 15 | MCP server logs to **stderr**; a fresh DB session per `call_tool` | stdio uses **stdout** for JSON-RPC — a stray log line there corrupts the protocol, so the entry point sets `basicConfig(stream=sys.stderr)`. The server is one long-lived process (not per-request), so each tool call opens its own `AsyncSessionLocal` (mirrors FastAPI's per-request session, minus the request) |
| Phase 15 | `pending_notes` migration uses `postgresql.ENUM(name='notetype', create_type=False)` | The `notetype` enum already exists (created by the notes-table migration). Without `create_type=False`, `op.create_table` re-emits `CREATE TYPE notetype` and the migration fails. The generic `sa.Enum` doesn't honor the flag reliably; the PostgreSQL-specific `postgresql.ENUM` does. `pending_notes` and `notes` share the one enum type — single-sourced |
| Phase 15 | `pending_notes` is a separate table; no `embedding`, no `updated_at` | Separate from `notes` so every `notes` row stays a real, approved, embedded note (no NULL-embedding half-rows) and no read path needs to know "pending" exists. No embedding because a pending note is never embedded — embedding happens once at approval on the final text. No `updated_at` because edits are cheap text `UPDATE`s and the row is short-lived (approved or rejected, then deleted) |
| Phase 15 | Reuse `NoteCreate`/`NoteUpdate` as the pending write/edit contracts; add only `PendingNoteResponse` | A pending note's writable shape *is* `NoteCreate` (approval must yield an identical note), so parallel create/update schemas would be drift. Only the response differs — it drops `updated_at`/`embedding` |
| Phase 15 | Separate `app/crud/pending.py`, one-way import from `crud/notes.py`; `approve_pending` promotes-then-deletes | `pending.py` imports `create_note`; `notes.py` stays ignorant of pending — no cycle. create_note commits before the pending delete, so a failed delete leaves a real note + a rejectable stale row, never a lost note. Spans two commits — accepted at personal scale |
| Phase 15 | Pending router: no HTTP `POST` create; reject=`DELETE` (204), approve=`POST …/approve` (returns `NoteResponse`, 201) | Staging is MCP-only, so an HTTP create endpoint would be unused. Reject removes a resource (DELETE); approve is a state transition that produces a new resource (the promoted note), so it returns the created note |
| Phase 15 | MCP `create_note` behavior sentence is per-surface; `NOTE_QUALITY_GUIDANCE` rides on the tool description | `/chat` "proposes an unsaved draft" vs MCP "stages a pending row" — different persistence, assembled per consumer. An MCP server can't set the host's system prompt, so the quality policy goes on MCP's tool description (weaker steering — accepted) |
| Phase 15 | Pending-tab Approve does `PUT`-then-approve; card values set as DOM properties, not attributes | Persisting the card's fields before promoting keeps inline edits (approval promotes what's in the DB). Assigning `.value` (vs an `innerHTML` `value="…"`) avoids Markdown quotes/backticks breaking the markup |
| Phase 15 | conftest: shared `engine` fixture + `db_session`, for seeding rows with no HTTP create path | Pending notes are staged only via MCP, so endpoint tests seed directly via `db_session` on the same engine `client` uses (committed rows visible to requests). `client`'s behavior is unchanged — additive split |
| Phase 15 | MCP write target = `DATABASE_URL` in the host's per-server env (no code change); never repoint local `.env`/global env | `load_dotenv(override=False)` makes the process env win over `.env`, so the host launches the server with `DATABASE_URL=Neon` while local dev/tests keep the Docker `.env`. A global OS env var or a repointed `.env` would leak Neon into the local app/tests — so scope it to the server's env block only |
| Phase 15 | Registered Claude Code with `claude mcp add <name> --scope user -- <direct script path>` (no `-m`, no `-e`, no `add-json`), env injected via a targeted string-replace on `~/.claude.json` | `add-json` rejects all input in CLI 2.1.152 (upstream bug); the flag form's `-e`/`--` handling breaks on any dash-prefixed arg. Since `app/mcp_server.py` is directly runnable (has `if __name__ == "__main__"`), pointing at the file avoids `-m` entirely, leaving zero dashes for the parser to trip on. **User scope**, not the CLI's local-scope default, stores the entry once at the top level of `~/.claude.json` (a sibling of `"projects"`), so the CLI, the VS Code extension, and the Claude Code shell inside Desktop all resolve to the same entry with no per-project keying to disagree about |
| Phase 16 | Split "Authentication + remote MCP" into Basic Auth (this phase) + a separate future Remote MCP phase | Research showed the OAuth/remote-MCP half is a substantial, self-contained build (new DB tables, an `OAuthAuthorizationServerProvider` implementation, Streamable HTTP transport wiring) vs. Basic Auth being a small, self-contained dependency addition — bundling would mix two different concerns into one large PR, against the project's one-phase-one-concern convention |
| Phase 16 | Router-level `dependencies=[Depends(get_current_user)]` at `include_router()`, not ASGI middleware | Matches the existing per-router registration style in `app/main.py`; `/health`'s exemption falls out for free by omitting the dependency on that one router, rather than needing path-based exclusion logic in a global middleware |
| Phase 16 | Fail closed on unset `BASIC_AUTH_USERNAME`/`PASSWORD` | `get_current_user` compares against `os.getenv(..., "")`; an unconfigured deploy locks everyone out rather than leaving every route open — the safer failure mode for a personal app |
| Phase 16 | Disable FastAPI's default `/docs`/`/redoc`/`/openapi.json` and re-add them behind auth | Router-level `dependencies=` doesn't cover FastAPI's built-in doc routes; leaving them open would keep the full API schema publicly browsable even though calls against it 401 — inconsistent with "not fully public" |
| Phase 16 | Static Client ID/Secret (not Dynamic Client Registration) for the future Remote MCP phase | Confirmed during this phase's planning: a single personal user with exactly one client that will ever connect (all of claude.ai's surfaces share one registration server-side) — DCR's value (supporting clients you don't know about in advance) doesn't apply |
| Phase 16 | Failed auth attempts logged at WARNING with no values | A wrong-credentials submission is a recoverable oddity (Phase 13 convention), not an ERROR; the log line never carries the submitted username/password. The browser's initial no-credentials challenge is raised by `HTTPBasic` before the dependency body runs, so routine prompt-triggers don't log |
| Phase 16 | `import_notes.py` reads Basic Auth credentials from `.env`, same file the local server reads | The gate broke the script's `POST /notes`; sharing the server's own `.env` means client and server credentials can't drift and no new config is introduced. Plain-http transport stays acceptable only because the target is loopback — repointing at the deployed app requires the `https://` URL |

---

## What is explicitly deferred

Do not build these until the relevant phase is reached:

- Remote MCP (OAuth 2.1 + Streamable HTTP transport) — future phase; local stdio MCP (Phase 15) and HTTP Basic Auth (Phase 16) are both done
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
| `app/embeddings.py`, `app/crud/notes.py` | Whole-note embedding — no chunking | Each note is embedded as a single vector, not split into overlapping chunks. Fine while notes are short; a long note dilutes into one averaged vector and loses retrieval granularity (semantic search can miss a relevant passage buried in a long note). If notes grow long enough for that to bite, add a chunking step: split `content` → embed each chunk → store/retrieve per-chunk vectors, citing the parent note. Requires a schema change (a `note_chunks` table or per-chunk rows) and touches both the write/embed path and the query path. Deferred as unneeded at current scale. |
| `app/models/note.py` | Phase 2 schema fields still unbuilt — tags, source, confidence, status | Deferred until usage patterns are clear. Revisit after the system has been in real use for a while. Requires Alembic migration + schema + CRUD updates. |
| `app/agent.py` | URL fetching in the draft agent | `/draft` is paste-only. Future: accept a URL, fetch the content server-side, pass to the agent. Adds meaningful complexity — defer until paste workflow is well-exercised. |
| `app/routers/ask.py`, `app/routers/assistant.py` | `/ask` vs `/chat` overlap | `/ask` is always-search-then-answer; `/chat`'s agent loop can do the same plus more. Decide whether `/ask` stays as a simpler single-shot option or eventually folds into `/chat`. |
| `app/assistant.py` | `/chat` conversation history is text-only | The loop replays prior user/assistant text but not `tool_use`/`tool_result` blocks, so cross-turn tool context isn't preserved. Fine at current scale; revisit if multi-turn tool continuity matters. |
| `app/database.py` | Engine + `DATABASE_URL` check run at import time | Importing the module requires a live `DATABASE_URL` and builds the engine eagerly — which is why CI had to set `DATABASE_URL` even though tests override the session. The lazy-init pattern used by `_client()` in `agent.py`/`llm.py`/`embeddings.py` would defer this so import doesn't depend on env. Low priority; the CI env var is a fine workaround. |
| `app/assistant.py`, `app/routers/assistant.py` | Request-correlation ID through the `/chat` loop (Phase 13 stretch, not built) | One `/chat` request fans out into several model calls logged as separate lines with no shared identifier, so concurrent requests interleave in the logs. Threading a request ID (e.g. via `logging` `extra=`/a filter) would let one turn's lines be grepped together. Deferred as over-engineering at single-user scale; revisit if concurrency or log volume makes interleaving a real problem. |
| `notes-inbox/`, `import_notes.py` | Legacy note-capture path now that MCP + pending/approve has landed | With Neon as the system of record and the MCP `create_note` → `pending_notes` → approve flow providing the review gate (Phase 15, code complete), the markdown-inbox workflow (which writes to *local* Docker via `import_notes.py` → `POST /notes`) is a second, divergent review path pointed at a different database. Decide whether to retire it or repoint it at Neon — once the MCP path is wired to a host and in real use. If repointed at the deployed app, `API_URL` must become the `https://` Render URL — the script now sends Basic Auth credentials (Phase 16), which is only safe over plain http because the current target is loopback. |

---

## Background on the developer

The developer brings 19 years of healthcare data experience with a background in actuarial science, modeling, and analytics. Has owned data pipelines end-to-end across production healthcare environments — from source system extraction through transformation, delivery, and stakeholder reporting.

Python and modern data engineering techniques are an active development focus. LearnStack is the primary vehicle: a deliberately sequenced project that builds backend and data engineering depth — async APIs, schema migrations, semantic search, LLM integration, agent loops, and cloud deployment — one pattern at a time.

The goal is to develop backend and data engineering proficiency to the level needed to succeed independently in data engineering and analytics engineering roles, particularly in health tech where domain expertise and technical depth both carry weight.

The project is deliberately chosen to build skills that transfer directly to those roles: FastAPI, Postgres, Docker, SQLAlchemy, Alembic, pytest, pgvector, LLM API integration (OpenAI, Anthropic), and RAG/semantic search.

Prefer explanations that connect new concepts to the developer's existing strengths in data modeling, logic, and analytical thinking. Avoid over-scaffolding; this developer learns well by doing.

---

## What makes a good note

RAG's value over a plain LLM conversation is specificity to *your* history —
not general knowledge you could re-derive or re-look-up at any time. Use this
to judge whether a suggested note is worth capturing:

**Good fit — capture these:**
- Project-specific facts, configs, and gotchas (e.g. "Render needs `plan: free`
  set explicitly or it defaults to Starter")
- Decisions and the *why* behind them (the kind of entry that belongs in the
  Decisions Log) — easy to re-litigate later if the reasoning isn't written down
- Errors and their fixes, especially ones tied to this project's specific setup
  (Docker images, env vars, dependency versions)
- Anything that "fades" — you understood it when it happened, but the specific
  detail (exact env var name, exact error string, exact workaround) won't stick

**Poor fit — skip or trim these:**
- General concepts you've understood well enough to retain or re-explain
  (e.g. "what `create_async_engine` does," "what a SQLAlchemy session is") —
  low retrieval value, since you could reconstruct or re-look-up the
  explanation easily
- Tutorials/how-tos that aren't tied to a project-specific decision or gotcha
- Patterns with no `project:` tag and no connection to LearnStack's own
  history — if it's pure general knowledge, a note doesn't add much

**When reviewing a suggested note:** if it reads like documentation anyone
could write, it's probably a poor fit. If it reads like "future-you would
otherwise have to re-debug or re-decide this," it's a good fit. When a note is
mixed (a general tutorial with one real gotcha buried in it), extract just the
project-specific part rather than keeping the whole thing.

---

## Note capture workflow

There are three intentional paths for capturing notes. All end up as rows in
the `notes` table — none is more "canonical" than the others.

**Browser path (web UI):** Use the Draft & Save tab at `/`. Paste raw content,
the `/draft` agent structures it into a draft note, you review and save via
`POST /notes`. Best when you're already in the browser or working from pasted
content (docs, Stack Overflow answers, etc.).

**Terminal / Claude Code path (markdown inbox):** Tell Claude Code "create a
note about X". It writes a new file to `notes-inbox/` using
`notes-inbox/_template.md` as the format and `examples/sample-note.md` as a
filled-in example. Best when you're heads-down in the terminal and don't want
to context-switch to a browser. Writes to whatever DB the running API targets
(local Docker in dev) — see the Follow-up on this becoming a divergent path.

**MCP path (Claude Code — Phase 15, wired):** Tell any Claude Code surface
(CLI, VS Code extension, or the Claude Code shell inside Desktop — one
registration covers all three) to capture a note; the MCP `create_note` tool
*stages* it into `pending_notes` (no embedding yet). You then review, edit,
and approve it in the web UI's **Pending** tab, which promotes it into
`notes` (embedding the final text). Pointed at `DATABASE_URL=<Neon>`, this is
the path that lands notes in the system-of-record DB behind a human review
gate. See `docs/phases/phase-15.md` → **MCP host wiring** for the registration sequence. Note:
`notes-inbox/` writes to *local* Docker, while this path targets Neon — they
are not the same database. (claude.ai's web/mobile chat apps are a separate,
not-yet-built remote-MCP phase — this path doesn't reach them.)

**To import inbox notes:** once the API is running, `python import_notes.py`
posts all `notes-inbox/*.md` files to `POST /notes` and moves them to
`notes-inbox/processed/`. The script authenticates with the
`BASIC_AUTH_USERNAME`/`PASSWORD` values from `.env` (Phase 16) — the same
ones the local dev server reads, so no separate setup. Failed files
(including 401s) stay in the inbox.

**Note:** `notes-inbox/processed/` is gitignored and only reflects notes
imported via `import_notes.py` on this machine — it is a local audit trail,
not a mirror of every note in the database, and won't exist on a fresh clone.
Notes created via the web UI or Swagger have no markdown counterpart either.
`examples/sample-note.md` is the one filled-in example kept under version
control for reference.

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
