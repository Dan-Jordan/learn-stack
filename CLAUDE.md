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

**Phase 12 — Complete ✓ (one manual step remaining)**

Phase 12 (Continuous Integration) shipped `.github/workflows/ci.yml` — `pytest` runs on every PR and push to `main` against a `pgvector/pgvector:pg15` service container, with **no API keys required**: an autouse fixture mocks the embedding seam and the LLM clients are already mocked. See the Phase 12 section below. **Remaining manual step:** enable the branch-protection rule on `main` in GitHub settings once the workflow has a green run.

**Sequencing note:** the next phase (Logging) is the second of two production-fundamentals phases, taken deliberately ahead of the Insights and Auth feature phases. The app already auto-deploys to Render on merge to `main`, so a merge gate and runtime observability matter more right now than added features.

**Phase 13 — Planned next (Logging).** Deliberate, leveled logging across the app's boundaries and error paths so the deployed app is observable. See the Phase 13 section below.

**Phase 14 — Planned (Insights).** A scheduled clustering pipeline over note embeddings. See the Phase 14 section below.

**Phase 15 — Planned (Authentication).** HTTP Basic Auth on the Render deployment so the app can be shared without being fully public. See the deferred list below; a full phase plan will be written when it comes up (Auth does not yet have a standalone phase section).

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
| 14 | Insights | A scheduled job clusters note embeddings into topics and labels them; `/insights` shows the results |
| 15 | Authentication | HTTP Basic Auth gates all routes; credentials set via env vars, changeable without code changes |

**Embedding model:** OpenAI text-embedding API (industry standard, fractions of a cent per note for personal use).

**Deferred to Phase 7 (now complete):** An agent that drafts notes from raw content (paste in a doc or Stack Overflow answer, get a structured note back).

**Deferred to Phase 8:** Job postings — a separate table with structured fields (company, role, status, URL). Not stored in the notes table.

---

## Phase 11 — Complete ✓

**Goal:** A `POST /chat` endpoint backed by a multi-tool agent loop. Unlike `/draft` (which forces a single tool via `tool_choice`), this agent has multiple tools available and decides — turn by turn — whether to search notes, draft a note, or just respond in text. ✓

**Why:** `/query`, `/ask`, and `/draft` each wrap one capability behind one endpoint with no decision-making. This phase introduces the agent-loop pattern (`tool_choice: "auto"`, multi-turn tool execution, conversation state) as its own learning milestone, distinct from Phase 14's batch/scheduling pattern.

Built:
- [x] `app/assistant.py` — `_TOOLS` (`search_notes`, `create_note`) and `run_assistant(messages, db)`: call the model with `tool_choice` defaulted to `"auto"` → if `tool_use`, dispatch to the matching `app/crud/notes.py` function and append a `tool_result` → repeat until the model responds in text or the `MAX_ITERATIONS = 5` cap is hit. `create_note` is confirm-before-save — it records the proposed draft in the trace and does **not** persist
- [x] `app/schemas/note.py` — `NOTE_TOOL_INPUT_SCHEMA` (shared `create_note` tool contract, referenced by both `agent.py` and `assistant.py`) plus the `/chat` schemas: `ChatRequest` (`{message, history}`), `ChatResponse` (`{reply, trace}`), `ToolCall`, and `ChatMessage`
- [x] `app/routers/assistant.py` — `POST /chat`: maps `{message, history}` to the Anthropic message list and returns the final text plus a trace of tools called
- [x] `app/main.py` — assistant router registered
- [x] `static/index.html` — new "Assistant" tab: a chat transcript (user/assistant bubbles + a tool-call trace line), distinct from the single-shot Ask tab. `create_note` proposals render as a card with a Save button (`POST /notes`)
- [x] `tests/test_assistant.py` — 7 tests; mock `app.assistant._client` with scripted tool-use/text responses to exercise the real loop (dispatch, termination, the iteration cap, confirm-before-save, graceful tool-error handling). 34 tests passing total

**Design decisions:**
- `tool_choice: "auto"` (achieved by omitting `tool_choice`) is the defining difference from `/draft`'s forced single tool — this is what makes it an agent rather than structured extraction
- **`create_note` is confirm-before-save (human-in-the-loop)** — the agent records the proposed draft in the response trace but never persists it; the user reviews and saves via `POST /notes`. Keeps junk out of the RAG store, consistent with `/draft`
- **Model: Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — consistent with `/draft` and `/ask`; cheapest model, sufficient for a 2-tool loop at personal scale
- **Hard cap `MAX_ITERATIONS = 5`** — prevents runaway looping; on cap, return the current text flagged with the limit
- **Shared `NOTE_TOOL_INPUT_SCHEMA`** — the `create_note` tool input schema is defined once in `app/schemas/note.py` and referenced by both `agent.py` and `assistant.py`, so the note shape can't drift. Per-field descriptions live in the shared schema; each caller supplies its own top-level tool `description`
- **Instruction placement** — trigger / when-to-call guidance lives on the tool `description`; the editorial "what makes a good note" policy lives in the `system` prompt (canonical copy is this file's "What makes a good note" section). DRY applies to contracts/schemas, not to prompt prose tuned per surface
- **Request uses client-supplied `history`, not `conversation_id`** — makes multi-turn work statelessly now (like `/ask`); a `conversation_id` would be a no-op without server-side storage, which stays deferred. History is text-only — `tool_use`/`tool_result` blocks are not replayed across turns; the loop re-derives tool use each message
- **`ToolCall.input` is `dict[str, Any]`** — deliberately loose so the response schema isn't coupled to the tool set; the `create_note` draft rides through this field for the UI's Save button
- `run_assistant(messages, db)` takes the DB session — the loop needs it to dispatch tool calls to `app/crud/notes.py`
- Launch with two tools (`search_notes` + `create_note`) — one read, one write — to keep the focus on the agent loop. `get_note` (by-ID fetch) and snippet-trimming are deferred: retrieval/cost optimizations, not agent-loop concepts
- Tool execution dispatches to existing `app/crud/notes.py` functions — no duplicated business logic; the agent is a new orchestration layer
- **Tests mock `app.assistant._client`, not `run_assistant`** — exercises the real loop; mocking the helper would test nothing. The `_client()` indirection is the test seam (see the Testing convention note below)
- `/draft` remains for "I have raw content, structure it"; the assistant is for "have a conversation, the model decides what to do" — not a replacement

**Open questions / follow-ups:**
- Cost: a single user message can trigger multiple API calls (search → reason → maybe draft) instead of `/ask`'s one
- Overlap with `/ask` — decide whether `/ask` stays as a simpler always-search-then-answer option or eventually folds into `/chat` (tracked in the Follow-ups table)

---

## Phase 12 — Complete ✓ (one manual step remaining)

**Goal:** A GitHub Actions workflow runs the full test suite against real Postgres + pgvector on every pull request, and a branch-protection rule requires that check to pass before merge to `main`. ✓ (workflow shipped; branch-protection rule is the remaining manual GitHub-settings step)

**Why:** `main` auto-deploys to Render on merge (Phase 10), but nothing currently stops a broken merge from shipping — the only safeguard was remembering to run `pytest` locally on Windows. CI closes that gap and adds a Linux test run matching the deploy target, catching environment-specific breakage before Render does. First of two production-fundamentals phases (CI, then logging) taken before resuming feature work.

Built:
- [x] `.github/workflows/ci.yml` — triggers on `pull_request` and pushes to `main`; Python 3.11 with pip cache, a `pgvector/pgvector:pg15` service container (health-checked with `pg_isready`), `pip install -r requirements.txt`, `CREATE EXTENSION IF NOT EXISTS vector`, then `pytest`. No secrets configured — the suite makes no live API calls
- [x] `tests/conftest.py` — autouse `mock_embeddings` fixture patches `app.crud.notes.embed_text` (the single seam feeding both the note-write and semantic-query paths) with a deterministic stand-in, so the suite needs no `OPENAI_API_KEY`
- [x] `tests/test_query.py` — `test_semantic_query_ranking` rewritten to inject **controlled** vectors (query ≡ SQLAlchemy note → score 1.0; Docker note orthogonal → score 0.0), testing the ordering/scoring code deterministically with no live call. Every test now runs on every PR — no skips, no marker
- [x] `README.md` / `CLAUDE.md` — CI gate and the no-secrets testing approach documented
- [ ] **Manual:** branch-protection rule on `main` (GitHub settings) — require the CI check to pass and the branch to be up to date before merge. Enable only after the workflow has a green run on a PR

Verified: `pytest` with no keys → 34 passed, 0 skipped — the entire suite (including ranking) runs deterministically and offline.

**Design decisions:**
- **Mock the embedding call rather than give CI a real `OPENAI_API_KEY`** — a merge gate must be deterministic and self-contained; a live model call can flake on model drift, network, or rate limits, and a gate that goes red for reasons unrelated to the diff trains you to ignore red. CI tests *your* code, not OpenAI's model. No secret also keeps the key out of CI entirely, consistent with `render.yaml`'s `sync: false` posture. The discovery that drove this: contrary to the original plan's assumption, most of the suite (`test_notes`, `test_query`, `test_ask`) made **live** embedding calls — it was never actually mocked
- **One autouse fixture patching a single seam (`embed_text`)** — both the write path and the query path funnel through it, so one patch neutralizes every live call. The stub is content-derived (deterministic per text) with non-negative components, which keeps cosine distance in `[0, 1]` and similarity scores in the `[0, 1]` range the tests assert
- **Ranking test uses controlled vectors, not the real API** — `test_semantic_query_ranking` asserts that the closest vector ranks first with the right score. The thing worth testing is *LearnStack's* ordering/scoring code, which is deterministic; *OpenAI's* semantic quality is its own concern and isn't LearnStack's to test. By injecting known vectors the test runs in CI on every PR with no key — rather than a `skipif`-gated live test that silently never runs (pytest doesn't load `.env`, so it would skip even locally). If a live smoke check of real embeddings is ever wanted, the right home is a separate scheduled workflow with a secret, not a test in the merge gate — deferred as over-engineering at personal scale
- **Prebuilt `pgvector/pgvector:pg15` service container** — avoids compiling pgvector from source the way the local `Dockerfile` does, so runs stay fast
- **`create_all`, not Alembic, in CI** — `conftest.py` builds the schema directly from the ORM models, so CI only needs the `vector` extension present (the service container creates the database via `POSTGRES_DB`); no migration step is required for the test run
- **Gate covers `pytest` only** — linting / type-checking are a deliberate later addition, not part of this phase

**Risks / gotchas (carried forward):**
- Branch protection on a solo repo can block your own merges if the check is misconfigured — confirm the workflow is green on a PR before enabling the rule (why it's left as a manual step)

---

## Phase 13 — Planned (Logging)

**Goal:** Deliberate, leveled logging across the app's boundaries and error paths — external API calls (OpenAI/Anthropic), database writes, and request/failure points — configured centrally and driven by an env var, so the running app (especially on Render) is debuggable.

**Why:** Logging today is a root `basicConfig` in `app/main.py` plus a single `logger.exception` in `app/assistant.py`. The rest — routers, `crud/notes.py`, `embeddings.py`, `llm.py`, `agent.py` — is silent, so a failed embedding, an empty search, or a timed-out API call on Render leaves no trace. This phase makes the deployed app observable. The emphasis is on the judgment of *where* and *at what level* to log — getting the full set of considerations right, not maximizing volume.

Planned components:
- [ ] Per-module loggers (`getLogger(__name__)`) across `app/`, generalizing the pattern already in `assistant.py`
- [ ] Log at boundaries: each OpenAI/Anthropic call (`embeddings.py`, `llm.py`, `agent.py`, `assistant.py`), note create/update/delete in `crud/notes.py`, and error paths in the routers
- [ ] Central config: log level from a `LOG_LEVEL` env var (added to `.env.example` and `render.yaml`); a format that includes timestamp + logger name + level
- [ ] (Stretch) request correlation — thread a request ID through the `/chat` agent loop so its multiple API calls are traceable as one unit; ties into the existing response `trace`
- [ ] `README.md` / `CLAUDE.md` — document the level convention and `LOG_LEVEL`

**Considerations to get right (the whole point — placement and level, not sprinkling):**
- **Level discipline** — a clear rule per level: INFO for state changes ("note created", "search returned N"), WARNING for recoverable oddities (0 results, a retry), ERROR/`exception` for failures. Avoid the everything-at-INFO and `print()` anti-patterns
- **Where to log** — at seams (request in/out, external calls, DB writes) and error paths, *not* inside pure logic where it becomes noise
- **What must never be logged** — API keys, full embedding vectors, raw note content / anything potentially sensitive
- **Cost of verbosity** — `httpx` is already quieted to WARNING; keep new logs from re-drowning the signal
- **Observability vs. the response `trace`** — the `/chat` trace is user-facing; logs are for the developer. Keep the two purposes distinct

**Scope boundary:** logging only. Metrics, distributed tracing, and error-aggregation services (Sentry, OpenTelemetry) are a deliberately separate, later concern — folding them in here would defeat "start simple."

**Risks / gotchas:**
- Cargo-cult logging — a `logger.info` on every function produces noise that's worse than silence; the value is entirely in placement and level
- Wrong-level inflation — logging recoverable conditions as ERROR trains you to ignore ERROR
- Leaking secrets/PII into logs is a real production failure mode, not a hypothetical

---

## Phase 14 — Planned (Insights)

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
│   ├── assistant.py         # Anthropic client — run_assistant() agent loop for /chat
│   ├── models/
│   │   └── note.py          # Note ORM model, NoteType enum, embedding column
│   ├── schemas/
│   │   └── note.py          # All Pydantic schemas: NoteCreate, NoteUpdate, NoteResponse,
│   │                        #   QueryRequest, QueryResult, AskRequest, AskResponse,
│   │                        #   DraftRequest, DraftResponse, ChatRequest, ChatResponse,
│   │                        #   ToolCall, ChatMessage; plus NOTE_TOOL_INPUT_SCHEMA
│   ├── routers/
│   │   ├── notes.py         # CRUD endpoints
│   │   ├── query.py         # POST /query — semantic search
│   │   ├── ask.py           # POST /ask — RAG answer generation
│   │   ├── draft.py         # POST /draft — notes agent
│   │   ├── assistant.py     # POST /chat — multi-tool notes assistant
│   │   └── health.py        # GET /health — health check for Render
│   └── crud/
│       └── notes.py         # Database operations: create, read, update, delete, search
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions: pytest on every PR/push against pgvector service container
├── tests/
│   ├── conftest.py          # Test DB setup/teardown + autouse embedding mock (no API key needed)
│   ├── test_notes.py        # 10 tests — CRUD and keyword search
│   ├── test_query.py        # 6 tests — semantic search
│   ├── test_ask.py          # 5 tests — RAG answer endpoint
│   ├── test_draft.py        # 6 tests — notes agent endpoint
│   └── test_assistant.py    # 7 tests — notes assistant agent loop
├── alembic/                 # Migration scripts
│   ├── env.py
│   └── versions/
├── static/
│   └── index.html           # Single-page web UI (Draft & Save, Notes, Ask, Semantic Search, Assistant)
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
| POST | `/chat` | Notes assistant — multi-tool agent loop; decides whether to search, draft, or reply; returns the reply plus a tool-call trace |
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
- **`tests/test_assistant.py` mocks one level deeper** — it patches `app.assistant._client` (not `run_assistant`) so the *real* agent loop runs, feeding scripted tool-use/text responses via `messages.create`'s `side_effect`. `app.assistant.notes_crud.search_notes_semantic` is also mocked to avoid real DB/embedding calls. This exercises tool dispatch, loop termination, and the `MAX_ITERATIONS` cap. The cap test supplies exactly `MAX_ITERATIONS` scripted responses, so a runaway loop would raise `StopAsyncIteration` — the test passing is itself proof the cap holds.
- **Embeddings are mocked suite-wide by an autouse fixture (`mock_embeddings` in `conftest.py`)** — it patches `app.crud.notes.embed_text`, the single seam both the note-write and semantic-query paths use, with a deterministic content-derived stub. This is what lets the whole suite (and CI) run with **no `OPENAI_API_KEY`** and make no live calls — every test runs on every PR, no skips. A test that needs *specific* embedding values (e.g. `test_semantic_query_ranking`) patches `app.crud.notes.embed_text` again inside the test with controlled vectors; the inner patch wins while active. Note: tests do **not** make live API calls — don't add a `skipif`-on-key test, since pytest doesn't load `.env` and it would silently never run. A genuine live smoke check belongs in a separate scheduled workflow with a secret, not in this suite.

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

---

## What is explicitly deferred

Do not build these until the relevant phase is reached:

- Authentication (Phase 15) — HTTP Basic Auth gating all routes; credentials via env vars
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
| `app/routers/ask.py`, `app/routers/assistant.py` | `/ask` vs `/chat` overlap | `/ask` is always-search-then-answer; `/chat`'s agent loop can do the same plus more. Decide whether `/ask` stays as a simpler single-shot option or eventually folds into `/chat`. |
| `app/assistant.py` | `/chat` conversation history is text-only | The loop replays prior user/assistant text but not `tool_use`/`tool_result` blocks, so cross-turn tool context isn't preserved. Fine at current scale; revisit if multi-turn tool continuity matters. |
| `app/database.py` | Engine + `DATABASE_URL` check run at import time | Importing the module requires a live `DATABASE_URL` and builds the engine eagerly — which is why CI had to set `DATABASE_URL` even though tests override the session. The lazy-init pattern used by `_client()` in `agent.py`/`llm.py`/`embeddings.py` would defer this so import doesn't depend on env. Low priority; the CI env var is a fine workaround. |

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

There are two intentional paths for capturing notes. Both end up as rows in
the `notes` table — neither is more "canonical" than the other.

**Browser path (web UI):** Use the Draft & Save tab at `/`. Paste raw content,
the `/draft` agent structures it into a draft note, you review and save via
`POST /notes`. Best when you're already in the browser or working from pasted
content (docs, Stack Overflow answers, etc.).

**Terminal / Claude Code path (markdown inbox):** Tell Claude Code "create a
note about X". It writes a new file to `notes-inbox/` using
`notes-inbox/_template.md` as the format and `examples/sample-note.md` as a
filled-in example. Best when you're heads-down in the terminal and don't want
to context-switch to a browser.

**To import inbox notes:** once the API is running, `python import_notes.py`
posts all `notes-inbox/*.md` files to `POST /notes` and moves them to
`notes-inbox/processed/`.

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
