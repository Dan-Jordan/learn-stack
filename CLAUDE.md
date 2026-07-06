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

**Phase 15 — Complete ✓**

Phase 15 stands up a local (stdio) MCP server that exposes LearnStack's notes tools — `search_notes` (read) and `create_note` (staged write) — over the Model Context Protocol, so any Claude Code surface (CLI, VS Code extension, or the Claude Code shell inside Desktop) can search and capture notes into the **Neon** system-of-record database. `create_note` stages to a new `pending_notes` table; the note is reviewed, edited, and approved in a new "Pending" tab in the web UI, and only then embedded and promoted into `notes`. Built read-first (`search_notes`) to stand up the whole server with zero write risk, then the gated write path.

**Code, merge, and host wiring are all done.** The branch merged to `main` (Render's startup migration created `pending_notes` in Neon — confirmed via `GET /pending` returning `200 []` on the live app), and the MCP server is registered with Claude Code at **user scope** in `~/.claude.json` — one entry, pointed at Neon's `DATABASE_URL`, that covers the CLI, the VS Code extension, and the Claude Code shell inside the Desktop app simultaneously (confirmed working across all three). See **Phase 15 → MCP host wiring** below for the working registration sequence, and for what's deliberately *not* covered by this phase (claude.ai's web/mobile chat apps, which need a remote server — a separate future phase).

Phase 14 (Neon database migration) is complete — production Postgres now lives on Neon, with the web service still on Render. See the Phase 14 section below.

**Future phases are unnumbered.** Completed phases keep their numbers as a historical record; upcoming work is listed in order *without* numbers, so phases can be reordered or inserted without renumbering everything downstream. The future phases below are in intended order.

**Future phase — Authentication + remote MCP (next up).** HTTP Basic Auth gates all routes so the app can be shared without being fully public, and the MCP server is exposed remotely (over HTTP, with auth) rather than only over local stdio. Bundled because standing up a public write endpoint is exactly when the app should stop being unauthenticated; may split if the remote-MCP auth (OAuth) proves heavy. No standalone section yet — a full plan will be written when it comes up.

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
| — | Authentication + remote MCP | HTTP Basic Auth gates all routes (env-var credentials); the MCP server is exposed remotely with auth |
| — | Insights | A scheduled job clusters note embeddings into topics and labels them; `/insights` shows the results |

**Embedding model:** OpenAI text-embedding API (industry standard, fractions of a cent per note for personal use).

**Deferred to Phase 7 (now complete):** An agent that drafts notes from raw content (paste in a doc or Stack Overflow answer, get a structured note back).

**Deferred to Phase 8:** Job postings — a separate table with structured fields (company, role, status, URL). Not stored in the notes table.

---

## Phase 11 — Complete ✓

**Goal:** A `POST /chat` endpoint backed by a multi-tool agent loop. Unlike `/draft` (which forces a single tool via `tool_choice`), this agent has multiple tools available and decides — turn by turn — whether to search notes, draft a note, or just respond in text. ✓

**Why:** `/query`, `/ask`, and `/draft` each wrap one capability behind one endpoint with no decision-making. This phase introduces the agent-loop pattern (`tool_choice: "auto"`, multi-turn tool execution, conversation state) as its own learning milestone, distinct from the Insights phase's batch/scheduling pattern.

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

## Phase 12 — Complete ✓

**Goal:** A GitHub Actions workflow runs the full test suite against real Postgres + pgvector on every pull request, and a branch-protection rule requires that check to pass before merge to `main`. ✓

**Why:** `main` auto-deploys to Render on merge (Phase 10), but nothing currently stops a broken merge from shipping — the only safeguard was remembering to run `pytest` locally on Windows. CI closes that gap and adds a Linux test run matching the deploy target, catching environment-specific breakage before Render does. First of two production-fundamentals phases (CI, then logging) taken before resuming feature work.

Built:
- [x] `.github/workflows/ci.yml` — triggers on `pull_request` and pushes to `main`; Python 3.11 with pip cache, a `pgvector/pgvector:pg15` service container (health-checked with `pg_isready`), `pip install -r requirements.txt`, `CREATE EXTENSION IF NOT EXISTS vector`, then `pytest`. No secrets configured — the suite makes no live API calls
- [x] `tests/conftest.py` — autouse `mock_embeddings` fixture patches `app.crud.notes.embed_text` (the single seam feeding both the note-write and semantic-query paths) with a deterministic stand-in, so the suite needs no `OPENAI_API_KEY`
- [x] `tests/test_query.py` — `test_semantic_query_ranking` rewritten to inject **controlled** vectors (query ≡ SQLAlchemy note → score 1.0; Docker note orthogonal → score 0.0), testing the ordering/scoring code deterministically with no live call. Every test now runs on every PR — no skips, no marker
- [x] `README.md` / `CLAUDE.md` — CI gate and the no-secrets testing approach documented
- [x] Branch-protection ruleset on `main` (GitHub settings) — requires the CI `test` check to pass and the branch to be up to date before merge; PRs required with **0 required approvals** (solo repo); deletions and force-pushes blocked. Enabled after the first green CI run on a PR

Verified: `pytest` with no keys → 34 passed, 0 skipped — the entire suite (including ranking) runs deterministically and offline. The first PR's CI run surfaced a real gap (the app required `DATABASE_URL` at import; not set in CI) — fixed in `ci.yml`, then green.

**Design decisions:**
- **Mock the embedding call rather than give CI a real `OPENAI_API_KEY`** — a merge gate must be deterministic and self-contained; a live model call can flake on model drift, network, or rate limits, and a gate that goes red for reasons unrelated to the diff trains you to ignore red. CI tests *your* code, not OpenAI's model. No secret also keeps the key out of CI entirely, consistent with `render.yaml`'s `sync: false` posture. The discovery that drove this: contrary to the original plan's assumption, most of the suite (`test_notes`, `test_query`, `test_ask`) made **live** embedding calls — it was never actually mocked
- **One autouse fixture patching a single seam (`embed_text`)** — both the write path and the query path funnel through it, so one patch neutralizes every live call. The stub is content-derived (deterministic per text) with non-negative components, which keeps cosine distance in `[0, 1]` and similarity scores in the `[0, 1]` range the tests assert
- **Ranking test uses controlled vectors, not the real API** — `test_semantic_query_ranking` asserts that the closest vector ranks first with the right score. The thing worth testing is *LearnStack's* ordering/scoring code, which is deterministic; *OpenAI's* semantic quality is its own concern and isn't LearnStack's to test. By injecting known vectors the test runs in CI on every PR with no key — rather than a `skipif`-gated live test that silently never runs (pytest doesn't load `.env`, so it would skip even locally). If a live smoke check of real embeddings is ever wanted, the right home is a separate scheduled workflow with a secret, not a test in the merge gate — deferred as over-engineering at personal scale
- **Prebuilt `pgvector/pgvector:pg15` service container** — avoids compiling pgvector from source the way the local `Dockerfile` does, so runs stay fast
- **`create_all`, not Alembic, in CI** — `conftest.py` builds the schema directly from the ORM models, so CI only needs the `vector` extension present (the service container creates the database via `POSTGRES_DB`); no migration step is required for the test run
- **Gate covers `pytest` only** — linting / type-checking are a deliberate later addition, not part of this phase

**Risks / gotchas (carried forward):**
- Branch protection on a solo repo can block your own merges if misconfigured — enabled only after a green PR run, and configured safely: **Required approvals: 0** (GitHub won't let you approve your own PR, so ≥1 would lock you out), with admin bypass left available as an escape hatch
- The app reads `DATABASE_URL` at import time, so CI must set it even though tests override the DB session — logged as a Follow-up (lazy engine init would remove the requirement)

---

## Phase 13 — Complete ✓

**Goal:** Deliberate, leveled logging across the app's boundaries and error paths — external API calls (OpenAI/Anthropic), database writes, and failure points — configured centrally and driven by an env var, so the running app (especially on Render) is debuggable. ✓

**Why:** Logging before this phase was a root `basicConfig` in `app/main.py` plus a single `logger.exception` in `app/assistant.py`. The rest — `crud/notes.py`, `embeddings.py`, `llm.py`, `agent.py` — was silent, so a failed embedding, an empty search, or a timed-out API call on Render left no useful trace. This phase made the deployed app observable. The emphasis was the judgment of *where* and *at what level* to log — getting the full set of considerations right, not maximizing volume.

Built:
- [x] `app/main.py` — central config: level driven by `LOG_LEVEL` (default INFO, safe fallback to INFO on an unrecognized value rather than crashing startup); format `"%(asctime)s %(levelname)s %(name)s: %(message)s"` so every line carries a timestamp + emitting module + level. Existing `httpx`→WARNING quieting kept
- [x] Per-module loggers (`getLogger(__name__)`) added to `embeddings.py`, `llm.py`, `agent.py`, `crud/notes.py`, generalizing the pattern already in `assistant.py`
- [x] External-call seams: DEBUG before the `embed_text` call (size only — fires per-write *and* per-search, too frequent for INFO) with an explicit `logger.error` on failure that carries the input size; INFO breadcrumbs before the discrete `/ask` (`generate_answer`) and `/draft` (`draft_note`) calls; INFO per `/chat` agent-loop iteration (which tools the model chose) plus a WARNING on the iteration cap
- [x] `crud/notes.py` — INFO on note create/update/delete (id and changed field names only); INFO with count on a semantic search that returns results, WARNING when it returns zero (placed in `search_notes_semantic` so `/query`, `/ask`, and `/chat` all share it)
- [x] `LOG_LEVEL` added to `.env.example` (with a comment listing valid values) and `render.yaml` (as a committed `value: INFO`, not a `sync: false` secret)
- [x] `README.md` / `CLAUDE.md` — `LOG_LEVEL` and the level convention documented

Verified: full suite stays green (34 passed). Log output was confirmed two ways without paid API calls — an isolated check that `LOG_LEVEL` toggles the DEBUG line on/off and the format renders correctly, and a targeted `pytest --log-cli-level=INFO` run showing the real `crud/notes.py` lines firing (`Created note <id> (type=...)`, `Updated note <id> (fields=['title'], re-embedded=False)`, `Semantic search returned N note(s)` / `... no notes`).

**Design decisions:**
- **`LOG_LEVEL` parsed with a safe fallback** — `getattr(logging, LOG_LEVEL.upper(), logging.INFO)` so a typo in the env var falls back to INFO instead of crashing the app on startup (a startup crash on Render is worse than a wrong level)
- **`LOG_LEVEL` is config-as-code (`value: INFO`), not a dashboard secret** — it isn't sensitive, so the default belongs in version control where it's visible and tracked; changing verbosity is a deliberate, reviewable edit-and-redeploy, unlike the `sync: false` API keys. Trade-off accepted: no dashboard-only flip without a deploy
- **Level rule, applied consistently:** DEBUG = high-frequency internal plumbing (`embed_text`) and request-shape detail; INFO = discrete user-facing operations and state changes (note create/update/delete, `/ask`, `/draft`, per-loop iteration, search-returned-N); WARNING = recoverable oddities (0 search results, iteration cap); ERROR/`exception` = failures
- **`logger.error` (re-raise) vs `logger.exception` (swallow)** — the deciding factor is whether the exception keeps propagating. If it's re-raised, log a one-line context message with `logger.error` and *no* `exc_info`, letting whoever finally handles it log the traceback (the ASGI handler, or the `/chat` loop) — this avoids duplicate tracebacks. If it's swallowed here (the agent loop's tool-dispatch `except`), use `logger.exception` because that's the only place the traceback gets captured
- **`embed_text`'s ERROR wrap earns its place by adding context, not visibility** — the failure is logged with a traceback either way (uvicorn, or the `/chat` loop). The wrap exists to carry the *input size*, which the traceback lacks and which distinguishes a token-limit failure from a transient one. Its pre-call breadcrumb is DEBUG (invisible in prod), so this is also the only embedding-specific signal at the prod level
- **Never log values** — only note ids, changed field *names*, sizes, and counts. No API keys, embedding vectors, raw note content, or question text
- **Routers deliberately left unlogged** — their only error paths are the `404` `HTTPException`s, which are expected client outcomes already recorded in uvicorn's access log; 500-class failures already get a traceback from uvicorn (or the `/chat` loop). Adding request logging would duplicate uvicorn and be exactly the cargo-cult the phase warns against

**Scope boundary:** logging only. Metrics, distributed tracing, and error-aggregation services (Sentry, OpenTelemetry) are a deliberately separate, later concern. The planned (stretch) request-correlation ID through the `/chat` loop was **not** built — deferred as over-engineering at personal scale; see Follow-ups.

**Risks / gotchas (carried forward):**
- Cargo-cult logging — a `logger.info` on every function is noise worse than silence; the value is entirely in placement and level. This drove the decision to leave the routers unlogged
- Wrong-level inflation — logging recoverable conditions as ERROR trains you to ignore ERROR (why 0-results is WARNING, not ERROR)
- Leaking secrets/PII into logs is a real production failure mode — mitigated by the never-log-values rule, but worth re-checking whenever a new log line is added

---

## Phase 14 — Complete ✓ (Neon database migration)

**Goal:** Move the production Postgres database off Render's free tier onto Neon's free tier, with no loss of notes and no change to local dev, tests, or CI. The web service stays on Render; only the database moves. Done when the deployed app on Render reads and writes against Neon, the existing notes have been migrated across, and `render.yaml` no longer provisions a Render database.

**Why:** Render's free Postgres instance is suspended after 30 days, so the database needs a new home regardless. Neon's free tier is genuinely free (not time-boxed), speaks standard Postgres, and — critically — supports `pgvector`, which the entire RAG stack depends on. Keeping the web service on Render and moving only the database to Neon is the smallest change that solves the expiry. (Supabase is the comparable free + pgvector alternative; Neon is a fine choice and not worth overthinking.)

**This is its own phase, not part of Insights.** It is time-sensitive (gated by Render's suspension date, whereas Insights is unhurried feature work) and a different concern (deployment/infrastructure, not clustering). Bundling an SSL/connection change with a KMeans feature into one PR would be hard to review and hard to roll back — so it stays a single coherent change, consistent with the one-phase-one-concern convention. Whether it carries a phase number is cosmetic; numbering it Phase 14 (and pushing Insights to 15) keeps the two unbundled, which is the point.

**Blast radius is small — production connection only.** Local dev, the test suite, and CI all use the Docker / CI `pgvector` container, not the cloud database, so they are untouched. No business logic moves — only the two database *connection* paths (`app/database.py` and `alembic/env.py`) plus `render.yaml`; this is a connection-string and config change plus a one-time data copy.

Built:
- [x] `app/database.py` — `split_ssl_args()` moves Neon's libpq-only TLS params out of the URL and into asyncpg's `connect_args`. It strips **both** `sslmode` *and* `channel_binding` (Neon's copy-paste string carries both; asyncpg rejects both), and passes `connect_args={"ssl": True}` when SSL was requested. For the local Docker URL (no `sslmode`) it is a no-op: query stays empty, `connect_args` comes back `{}`, behavior unchanged — so local dev, tests, and CI are untouched
- [x] `alembic/env.py` — the migration engine calls the **same** `split_ssl_args()` (imported from `app.database`). This was the first-deploy fix: `env.py` built its own engine straight from `DATABASE_URL`, bypassing the helper, so `alembic upgrade head` crashed on the `sslmode` param before the app started even though the app engine was already fixed. Both connection paths now share one helper and can't drift
- [x] `render.yaml` — `databases:` block removed (Render no longer provisions the database). `DATABASE_URL` stays a `sync: false` dashboard secret; the Neon connection string (scheme `postgresql+asyncpg://`, params stripped at runtime by the code above) is pasted into the Render Environment tab
- [x] Neon project created (`learnstack`, Postgres 18.4, AWS us-west-2 / Oregon — co-located with the Render web service to minimize cross-DC latency). The **direct** (non-pooler) endpoint is used. `pgvector` 0.8.1, installed by the startup migration's `CREATE EXTENSION IF NOT EXISTS vector`
- [x] Render redeploy against Neon — live. Deployed via merge to `main` (auto-deploy) with the SSL fix in place, after the `DATABASE_URL` secret had been staged with "Save only". (The Neon password was rotated mid-migration after being shared during setup; the new value was set in Render before the successful deploy.)
- [x] Data migration — existing notes copied from local Docker Postgres into Neon with `pg_dump -t notes` → `pg_restore --data-only -t notes` (the startup migration created the schema first)
- [x] `README.md` / `CLAUDE.md` — deployment docs, phase list, and tech-stack tables point the database at Neon; decisions and gotchas recorded in the decisions log
- [x] `notes-inbox/` — the connection gotchas captured as notes (asyncpg can't parse `sslmode`/`channel_binding`; direct vs pooler endpoint; deploy ordering), imported to the notes DB

Verified: locally against live Neon before deploy — connecting through `app.database` succeeds; engine receives `...neon.tech/neondb` (no `sslmode`/`channel_binding`) with `connect_args={'ssl': True}`; server reports PostgreSQL 18.4; `pgvector` 0.8.1. After the `env.py` fix, `alembic upgrade head` against Neon cleared the `sslmode` parse and reached real authentication. Installed driver versions: SQLAlchemy 2.0.50, asyncpg 0.31.0 — `connect_args={"ssl": True}` is the correct form for these. Full suite stays green (34 passed) — the change is a no-op for the no-SSL local/CI URL.

**Design decisions:**
- **Move only the database, keep the web service on Render** — the web service free tier is not expiring; the database is. The smallest change that fixes the actual problem
- **Neon over staying on Render / over Supabase** — Render's free Postgres is the thing expiring, so staying isn't an option. Neon is picked over Supabase only on simplicity-of-fit; both are free with pgvector. Not worth deeper evaluation at personal scale
- **Declined Neon's add-ons (Neon Auth / "Backend Services", `neonctl init` AI tooling)** — Neon Auth is a multi-user identity system (users/sessions tables, OAuth); the project's upcoming Authentication phase is deliberately single-user HTTP Basic Auth, and multi-user is explicitly not planned. Adopting it would also couple the app to a Neon-specific product, cutting against this phase's whole point (staying DB-agnostic so the next move is cheap). Created a plain Postgres project, nothing else
- **Direct endpoint over the pooler** — avoids the asyncpg-prepared-statements-vs-PgBouncer problem entirely for a single low-traffic service, rather than carrying a `statement_cache_size=0` workaround for pooling the app doesn't need
- **SSL via `connect_args`, both `sslmode` and `channel_binding` stripped from the URL** — asyncpg's TLS is configured through the driver (`connect_args={"ssl": True}`), not libpq URL params. Neon's copy-paste string carries *both* `sslmode=require` and `channel_binding=require`, and asyncpg rejects both; stripping only `sslmode` would leave the second as a hidden second failure. The stripping is implemented generically (`split_ssl_args`, shared by the app engine and the Alembic migration engine) so the local URL with no such params is unaffected
- **`DATABASE_URL` stays a dashboard secret (`sync: false`)** — unchanged posture from Phase 10; the connection string (now Neon's) is still set in the Render dashboard, never committed
- **No business logic moves** — `crud/`, `routers/`, logging, and the agent loops are all DB-agnostic; this phase touches only the two DB *connection* paths (`app/database.py`, `alembic/env.py`) and `render.yaml`
- **The SSL helper is shared between the app engine and the migration engine** — the original fix only covered `app/database.py`; the first deploy crashed because `alembic/env.py` builds its own engine and bypassed it. Both now import one `split_ssl_args()` so the two connection paths handle Neon identically and can't drift. (This is the same contract-DRY principle the Phase 11 note records — share the contract, not context-tuned prose)

**Risks / gotchas:**
- **Time-sensitive** — the data copy must happen before Render suspends the instance, or the notes are gone. This is the one hard deadline in the phase
- **Deploy order matters** — the SSL-stripping fix must be on `main` *before* the live app points at Neon. Pointing the deployed (pre-fix) app at the Neon URL would crash-loop on the `sslmode` param. Mitigated by saving the Render `DATABASE_URL` with "Save only" (no deploy) and letting the merge-triggered deploy pick it up with the fix in place
- **asyncpg + `sslmode`/`channel_binding`** — the first-deploy failure mode; the URL must have both stripped and SSL passed via `connect_args` (handled by `split_ssl_args`, used by both the app and migration engines)
- **Pooler vs direct endpoint** — using the `-pooler` host with asyncpg's default prepared-statement caching causes intermittent failures; use the direct host (or `statement_cache_size=0`)
- **Cold-start latency** — Neon autosuspends on idle; the first request after a quiet period is slow (Neon takes ~1–3s to wake). Inherent and accepted on a free tier. Separately, autosuspend *drops* pooled connections, so without a liveness check that first request would also *error* (a dead connection from the pool) — handled by `pool_pre_ping=True` on the engine; see the decisions log
- **`DATABASE_URL` scheme** — must be `postgresql+asyncpg://` (not Neon's default `postgres://`), same conversion already noted for Render

---

## Phase 15 — Complete ✓

**Goal:** A local (stdio) MCP server exposes LearnStack's notes tools — `search_notes` (read) and `create_note` (staged write) — over the Model Context Protocol, so any Claude Code surface (CLI, VS Code extension, or the Claude Code shell inside Desktop) can search and capture notes that land in the **Neon** system-of-record database. `create_note` stages to a new `pending_notes` table; the note is reviewed, edited, and approved in a new "Pending" tab in the web UI, and only then embedded and promoted into the `notes` table. Done when: from Claude Code, "create a note about X" stages a pending note in Neon, and approving it in the Pending tab produces a `notes` row identical to one created any other way.

**Why:** Two things at once. (1) It builds the **provider side** of the agent/tool pattern — Phase 11 built the *host* side (the `/chat` loop that decides which tool to call); this exposes tools *over the protocol* so any host can use them. That's a distinct, marketable skill (MCP is the default integration layer across the industry), and having both sides demonstrates the whole pattern. (2) It fixes a real, felt sync problem: notes captured from Claude Code currently reach only **local** Docker via `import_notes.py`, so Neon — what the deployed app reads — drifts. With Neon as the system of record and the MCP `create_note` pointed at `DATABASE_URL` (= Neon), capturing from Claude Code lands the note in production, behind a review gate. The staged-write gate applies the "nothing writes to the system of record without a checkpoint" instinct to an agentic interface — a data-governance pattern, not just a wired-up function call.

**Internal build sequence (one phase, ordered for learning):**
1. **`search_notes` (read-only) first** — stands up the entire MCP server: server, tool discovery, schema, stdio transport, connecting Claude Code to it. Zero write risk, so this is where the pure "learn MCP" work lives. Reuses `crud.search_notes_semantic`.
2. **`create_note` (write)** — stages to the new `pending_notes` table. Does **not** touch `notes` and does **not** embed.
3. **"Pending" review** — the web-UI tab to list / edit / approve / reject staged notes. Approve calls the **existing** `crud.create_note` (embeds the final text, inserts into `notes`, deletes the pending row).

The gate (steps 2–3) does not have to be built in lockstep with the `create_note` step during branch dev, but it **must be in place before the phase merges to `main`** — merge auto-deploys and points the live tool at Neon, so no ungated write to the system of record may ship.

**Built:**
- [x] `app/prompts.py` (new) — shared model-steering prose: `SEARCH_NOTES_TOOL` (full def), `CREATE_NOTE_TRIGGER`, `NOTE_QUALITY_GUIDANCE`, moved out of `assistant.py`. **Landed in a new `app/prompts.py`, not `schemas/note.py` as first sketched** — the prose is a different concern from the Pydantic models; `NOTE_TOOL_INPUT_SCHEMA` (the note *data contract*) stays in `schemas/note.py` beside `NoteCreate`. `app/agent.py` also adopted `NOTE_QUALITY_GUIDANCE`.
- [x] `app/assistant.py` / `app/agent.py` — consume the shared constants. `/chat`'s `_SYSTEM` and `create_note` description are byte-identical to before; `/draft`'s guidance now uses the shared wording.
- [x] `app/mcp_server.py` (new) — **low-level `mcp.server.Server`, not FastMCP** (see decisions). `list_tools()` advertises **both** `search_notes` and `create_note`, each reusing the shared name/description/schema (schema value re-keyed `input_schema`→`inputSchema`). `call_tool()` routes to `_search_notes` / `_create_note`, each on a per-call `AsyncSessionLocal`: `_search_notes` → `crud.search_notes_semantic`; `_create_note` builds a Pydantic-validated `NoteCreate` and stages it via `crud.pending.create_pending` (never writes `notes`, never embeds), returning a "staged for review" confirmation with the pending id. DB target via `DATABASE_URL`; logging goes to **stderr** because stdout is the JSON-RPC channel.
- [x] Alembic migration + `PendingNote` model — new `pending_notes` table with the writable `NoteCreate` fields (`title`, `content`, `note_type`, `tool`, `project`, `topic`) plus `id` and `created_at`. **No embedding column** — embedding happens only on promotion to `notes`. Model in `app/models/note.py`; migration `daf904df7559` uses `postgresql.ENUM(create_type=False)` so it doesn't re-create the existing `notetype` enum.
- [x] `app/crud/pending.py` (new) — `create_pending`, `get_pending`, `list_pending`, `update_pending`, `approve_pending` (→ calls existing `crud.notes.create_note`, then deletes the pending row — promote-then-delete), `reject_pending`. One-way import from `crud/notes.py`, no cycle.
- [x] `app/routers/pending.py` (new) — `GET /pending` (list), `PUT /pending/{id}` (edit, reuses `NoteUpdate`), `POST /pending/{id}/approve` (promote → `NoteResponse`, 201), `DELETE /pending/{id}` (reject, 204). **No HTTP create** — staging is MCP-only. Registered in `app/main.py`.
- [x] `static/index.html` — new "Pending" tab: lists staged notes as inline-editable cards; Approve persists edits (`PUT`) then promotes (`POST …/approve`); Reject deletes behind a `confirm()`. Lazy-loads on first open with a Refresh button.
- [x] `tests/` — `test_mcp.py` (6: tool discovery + dispatch, mock crud); `test_pending.py` (8: CRUD + endpoints incl. approve-promotes-and-embeds, embedding covered by the autouse `mock_embeddings` fixture). `conftest.py` gains a shared `engine` fixture + a `db_session` fixture to seed pending rows (no HTTP create path).

Verified: full suite green — **48 passed** (14 new: 8 pending + 6 MCP). Approve flow smoke-tested end-to-end against the live app: `PUT` edit → `POST …/approve` promotes with the edit, note lands in `notes` (embedded), pending queue empties. The MCP server boots cleanly (`python -m app.mcp_server`) and stages `create_note` into `pending_notes`. Post-merge, the live Render app's `GET /pending` returns `200 []`, confirming the startup migration created `pending_notes` in Neon. The MCP server is registered with Claude Code at **user scope** — one entry in `~/.claude.json` covers the CLI, the VS Code extension, and the Desktop app's Claude Code shell — env pointed at Neon's `DATABASE_URL`. See **MCP host wiring** below for the registration sequence.

**Design decisions:**
- **One phase, internally sequenced read → write → review**, gate present before merge — keeps concepts unmixed while never shipping an ungated write to the system of record.
- **Local (stdio) transport; DB target config-driven via `DATABASE_URL` (set to Neon).** Solves the sync problem immediately and privately (stdio is you-only by construction); going remote later is an additive layer (transport + auth), reused wholesale — that's the separate **Authentication + remote MCP** phase, not this one.
- **Neon = system of record; local Docker = dev/test scratch.** The MCP write path targets Neon; this is the project accepting that Neon, not local, holds the real notes.
- **Staged writes = a separate `pending_notes` table, not a `status` column on `notes`.** Keeps the `notes` table invariant clean (every row is a real, approved, embedded note — no NULL-embedding half-rows), so no read path — present or future, embedding-based or not — needs to know "pending" exists. Editing a pending note is a cheap text `UPDATE`; **embedding happens once, at approval, on the final text**, never on a draft still being edited or one that gets rejected.
- **Reuse the existing note contract and write path.** MCP `create_note` uses `NOTE_TOOL_INPUT_SCHEMA`; approval calls the existing `crud.create_note`, so an approved note is byte-for-byte the same shape as any other. The `notes-inbox/_template.md` frontmatter/body maps 1:1 onto those same fields — the markdown template and the schema are two views of one note shape, so the MCP path honors the template without routing through a `.md` file.
- **DRY the prompt assets, truthfully.** `search_notes` is shared verbatim; `NOTE_QUALITY_GUIDANCE` and the `create_note` trigger are shared; `/chat` keeps the guidance in its **system prompt** while MCP carries it on the **tool description** (MCP servers can't set the host's system prompt). The one intentionally *un*-shared bit is `create_note`'s behavior sentence — `/chat` "proposes a draft in the trace, never persists" vs MCP "stages a pending row" — because the surfaces genuinely persist differently. Share the contract and the policy; keep surface-specific behavior prose per surface (Phase 11 principle). **The shared prose lives in a new `app/prompts.py`, not `schemas/note.py`** — prose that steers a model is a different concern from Pydantic validation. `NOTE_TOOL_INPUT_SCHEMA` stays in `schemas/note.py` because it *mirrors `NoteCreate`* (two views of one note shape, kept adjacent so they can't drift); `prompts.py` imports nothing from `note.py`, so there's no cycle, and each `create_note` tool def is assembled at its consumer from prose (`prompts`) + schema (`note`).
- **Low-level `mcp.server.Server`, not FastMCP.** FastMCP is a convenience wrapper that *generates* a tool's JSON schema *from* a typed Python function (introspecting the signature / Pydantic `Field`s). It cannot consume a pre-built schema dict. But `NOTE_TOOL_INPUT_SCHEMA` already exists as data and is already fed to the Anthropic Messages API in `/chat` and `/draft` — so the note contract *must* live as a dict, shared by three consumers. Low-level `Server` takes that dict directly (`types.Tool(inputSchema=…)`), keeping one source of truth; FastMCP would force a second definition (a function signature / Pydantic model) and reintroduce the drift Phase 15 step 1 removed. The plan's word "FastMCP" was shorthand for "an MCP server"; its stronger commitment ("reuse the shared def") wins. Bonus: the low-level API also exposes MCP's real mechanics — tool *discovery* (`list_tools`) and *dispatch* (`call_tool`) — which mirror the `/chat` loop's own dict-of-tools + dispatch-by-name model.
- **stdout is the protocol; logs go to stderr.** The stdio transport uses stdout for JSON-RPC. `app/mcp_server.py`'s entry point calls `basicConfig(stream=sys.stderr, …)` so `crud`/`embeddings` log lines can't corrupt the channel. (The FastAPI app's `basicConfig` in `main.py` never runs for the MCP server — it's a separate entry point.)
- **Keep `app/assistant.py` / `/chat`.** Different surface and audience — an in-app assistant that needs no Claude client, vs. a bring-your-own-Claude host pointed at the MCP server. Keeping both shows both sides of the protocol; they share `crud` + schema, so there's one source of truth for behavior with two front doors (as `/draft`, `/chat`, and REST `/notes` already coexist).
- **Review/edit/approve happens in the web-UI "Pending" tab** — a human checkpoint at a real UI, the durable version of the ephemeral review gate `/draft` already provides.
- **`PendingNoteResponse` is the only new schema; reuse `NoteCreate`/`NoteUpdate` as the pending write/edit contracts.** A pending note's *writable* shape **is** `NoteCreate` by design (approval must produce an identical note), so parallel `PendingNoteCreate`/`Update` schemas would be drift waiting to happen. Only the *response* differs — it drops `updated_at` and `embedding` (the model has neither).
- **Separate `app/crud/pending.py`, imported one-way from `crud/notes.py`.** `pending.py` imports `create_note`; `notes.py` knows nothing about pending — no cycle. `approve_pending` **promotes then deletes** (create_note embeds+inserts+commits first, then the pending row is deleted) so a failed delete leaves a real note + a rejectable stale row, never a lost note. This spans two commits — accepted at personal scale.
- **Pending router has no HTTP `POST` create; reject is `DELETE`, approve is `POST …/approve`.** Staging happens only through MCP (`crud.create_pending`), so an HTTP create endpoint would be unused. Reject is a plain resource removal (`DELETE`→204); approve is a state transition that *produces* a new resource, so it returns the created `NoteResponse` (201).
- **MCP `create_note`'s behavior sentence is per-surface; the quality policy rides on the tool description.** `/chat` says "proposes an unsaved draft"; MCP says "stages a pending row" — genuinely different persistence, so the sentence is assembled at each consumer. Because an MCP server can't set the host's system prompt, `NOTE_QUALITY_GUIDANCE` rides on MCP's tool *description* (weaker steering than `/chat`'s system prompt — an accepted limitation).
- **Pending-tab Approve does `PUT`-then-approve; card field values are set as DOM properties, not HTML attributes.** Approve persists the card's current field values before promoting, so inline edits aren't lost (approval promotes what's in the DB). Field values are assigned via `.value` (not interpolated into an `innerHTML` `value="…"`) so Markdown content with quotes/backticks can't break the markup.
- **conftest: shared `engine` fixture + a `db_session` fixture.** Pending notes have no HTTP create path, so endpoint tests seed rows directly via `db_session` on the *same* engine the client uses (committed rows are visible to requests). The `client` fixture's behavior is unchanged — the split is purely additive.
- **Registered with Claude Code at user scope (`--scope user`), not the CLI's local-scope default.** Local scope nests a server's config under a key computed from the literal project working-directory string — case-sensitive, despite Windows paths being merely case-*preserving*, and computed inconsistently between the bare CLI and a VS Code-hosted session (confirmed: the two could resolve to different keys from the same repo). User scope stores the `learnstack` entry once, at the top level of `~/.claude.json` (a sibling of `"projects"`, not nested under any path), so the CLI, the VS Code extension, and the Claude Code shell inside the Desktop app all resolve to the exact same entry — no per-project keying left to disagree. Trade-off accepted: the server's tools are available in every Claude Code session for this user account, not scoped to just this repo — fine for a personal notes server.

**Risks / gotchas:**
- **No ungated write to Neon may ship** — the gate must be in place before merge, because merge auto-deploys and points the live `create_note` at Neon. (The gate — staged writes + Pending tab — is now complete.)
- **Never embed a pending note** — pending notes have no embedding, so they're absent from every embedding-based path automatically; any *new* "all notes" query must read `notes`, not `pending_notes`.
- **The local stdio server does not change the public-exposure posture** — it's private by construction. Do **not** expose the MCP server over HTTP in this phase; remote exposure + auth is the next phase, deliberately paired with locking the app down.
- **MCP hosts can't be given a system prompt by the server** — note-quality steering is weaker than inside `/chat`; mitigated by putting `NOTE_QUALITY_GUIDANCE` on the tool description.
- **`notes-inbox/` + `import_notes.py` become a divergent legacy review path** (writes to *local*, while the real gate now targets Neon) — flagged in Follow-ups; decide retire-vs-repoint after this phase lands, not before.
- **`claude mcp add-json` is broken in Claude Code CLI 2.1.152** — it rejects even trivially valid JSON (e.g. `{"command":"python"}`) with a generic `Invalid configuration: : Invalid input`, regardless of payload content or quoting style. A known upstream bug, not a project-specific mistake — re-check on CLI upgrade in case it's fixed.
- **`claude mcp add`'s flag form breaks on *any* dash-prefixed token after `--`**, not just `-m` as originally documented. Commander's argument parser loses the required positional `commandOrUrl` entirely if `-e KEY=value` is combined with `--`, or if any subprocess arg after `--` starts with `-` (confirmed with `--version`, `-m`, `-File`). The only combination that reliably works is `claude mcp add <name> -- <bare command> <bare args>` with **zero** dashes anywhere after `--` and **no** `-e` flags at all.

**MCP host wiring — complete.** The mechanism: `app/database.py` calls `load_dotenv(override=False)`, so a `DATABASE_URL` set in the MCP server's *process env* **wins over the repo `.env`** — the server hits Neon while the local web app and `pytest` keep using the Docker `.env`. **Do not repoint the repo `.env` at Neon** (that would send local dev and tests to production) and **do not set `DATABASE_URL=Neon` as a global OS env var** (same reason — it would leak into the local app). Set Neon *only* in the server's env block in `~/.claude.json`.

1. ~~Merge to `main`~~ — done; `GET /pending` on the live Render app returns `200 []`, confirming `pending_notes` exists in Neon.
2. ~~Register with Claude Code~~ — done, at **user scope**, which covers the CLI, the VS Code extension, and the Claude Code shell inside the Desktop app from one entry (confirmed connected from all three). The working sequence:
   ```powershell
   # 1. Register the bare command at user scope — no -e, no dashes after --, or the parser breaks:
   claude mcp add learnstack --scope user -- C:/Projects/learn-stack/.venv/Scripts/python.exe C:/Projects/learn-stack/app/mcp_server.py
   # (this creates the entry with an empty "env": {} placeholder, at the top level of ~/.claude.json —
   #  a sibling of "projects", not nested under any project path)

   # 2. Fill the env block via a temp .ps1 (keeps secrets out of PSReadLine's persisted
   #    interactive-command history — typing/pasting them at the prompt directly does not):
   $path = "$HOME\.claude.json"
   $content = [System.IO.File]::ReadAllText($path)
   $newEnv = '"env": {"DATABASE_URL": "<NEON_URL>", "OPENAI_API_KEY": "<OPENAI_KEY>", "PYTHONPATH": "C:/Projects/learn-stack"}'
   $content = $content.Replace('"env": {}', $newEnv)
   [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
   ```
   `python -m app.mcp_server` is deliberately not used — pointing at the script path directly (`app/mcp_server.py` has an `if __name__ == "__main__":` entry point) avoids the `-m` flag and its parser bug entirely. `PYTHONPATH` still matters so `app.*` imports resolve regardless of the host's own cwd. `.Replace('"env": {}', ...)` replaces every match in the file, not just the one you want — check the diff before saving.
3. **`env` contents.** `DATABASE_URL` = the Neon string (scheme `postgresql+asyncpg://…`, keep `?sslmode=…&channel_binding=…` — the app strips them). `OPENAI_API_KEY` is only needed for `search_notes` (embedding the query); `create_note` doesn't embed. `PYTHONPATH` = repo root.
4. **Verify.** From any of the three surfaces above: "save a LearnStack note about X" → `create_note` stages it → review/approve in the **Pending** tab of an app instance pointed at the *same* DB (the deployed Render app for Neon, or a local app run with `DATABASE_URL=<Neon>`). Note: a note staged into Neon will **not** appear in your local-Docker Pending tab — that's by design. Also note the MCP connection is picked up at Claude Code session **startup** — a session already running before registration won't see the new tools until restarted.

**Out of scope for this phase:** claude.ai's web and mobile chat apps — and Claude Desktop's own "Connectors" settings, distinct from its Claude Code shell above — can't reach a local subprocess at all; they only connect to remote MCP servers over HTTPS with OAuth. That's the separate, not-yet-built **Authentication + remote MCP** phase, confirmed (via Anthropic's docs) to cover claude.ai web, Claude Desktop, and the mobile apps from one registration once built — not a gap in this phase.

Full user-facing setup instructions live in `README.md` → **MCP server**.

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
│   ├── mcp_server.py        # Local stdio MCP server (low-level mcp.server.Server) — search_notes + create_note (staged)
│   ├── prompts.py           # Shared tool prose: SEARCH_NOTES_TOOL, CREATE_NOTE_TRIGGER, NOTE_QUALITY_GUIDANCE
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
│   └── test_mcp.py          # 6 tests — MCP tool discovery + dispatch (search + staged create)
├── alembic/                 # Migration scripts
│   ├── env.py
│   └── versions/
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

---

## What is explicitly deferred

Do not build these until the relevant phase is reached:

- Authentication (future phase — bundled with remote MCP) — HTTP Basic Auth gating all routes; credentials via env vars
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
| `notes-inbox/`, `import_notes.py` | Legacy note-capture path now that MCP + pending/approve has landed | With Neon as the system of record and the MCP `create_note` → `pending_notes` → approve flow providing the review gate (Phase 15, code complete), the markdown-inbox workflow (which writes to *local* Docker via `import_notes.py` → `POST /notes`) is a second, divergent review path pointed at a different database. Decide whether to retire it or repoint it at Neon — once the MCP path is wired to a host and in real use. |

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
gate. See Phase 15 → **MCP host wiring** for the registration sequence. Note:
`notes-inbox/` writes to *local* Docker, while this path targets Neon — they
are not the same database. (claude.ai's web/mobile chat apps are a separate,
not-yet-built remote-MCP phase — this path doesn't reach them.)

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
