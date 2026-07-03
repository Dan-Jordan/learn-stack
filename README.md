# LearnStack

A personal technical knowledge system built from the ground up — designed to help you capture, organize, retrieve, and grow what you know.

## The vision

The destination is a **RAG-powered learning system**: a knowledge base you can have a conversation with. You ask "what have I learned about dbt testing?" or "what errors have I run into with Docker Compose?" and the system retrieves the relevant notes you actually wrote, grounds its answer in them, and cites its sources. Not a generic LLM response — a response drawn from your own captured experience.

That capability — Retrieval-Augmented Generation, or RAG — is built on a simple foundation: your notes get converted into vector embeddings that encode meaning, and when you ask a question the system finds the notes whose meaning is closest to your question and hands them to the model as context. The result is answers that are grounded in what *you* know, not just what the model was trained on.

LearnStack is not a second brain. It is a backend application that earns its complexity over time — including, now, a multi-tool agent loop that can search your notes, draft new ones, and decide which to do on its own. But it is being built toward something specific: a system where your saved knowledge actively helps you keep learning.

---

## What it does today

- Save technical notes with structured metadata (type, tool, topic, project)
- Retrieve and search notes by keyword
- Query notes by meaning via `POST /query` — semantic search using vector embeddings
- Ask natural language questions via `POST /ask` — returns a grounded answer with source citations drawn from your own notes
- Draft structured notes from raw pasted content via `POST /draft` — paste a doc, Stack Overflow answer, or any text and get a structured note back for review
- Chat with a multi-tool assistant via `POST /chat` — an agent loop that decides per turn whether to search your notes, draft a new one, or just reply; drafted notes are returned for review, never auto-saved
- Full CRUD via a FastAPI REST API
- Single-page web UI at `/` — Draft & Save, Notes, Pending, Ask, Assistant, and Semantic Search tabs; no JSON editing required
- Capture notes from any MCP host (Claude Code, Claude Desktop) via a local stdio MCP server exposing `search_notes` (read) and `create_note` (staged write) — captured notes land in a review queue, surfaced in the web UI's **Pending** tab, and are only embedded into your notes on approval
- Postgres backend with pgvector extension, schema managed by Alembic migrations
- Embeddings generated automatically on note create/update via OpenAI text-embedding API
- Two note capture paths: the web UI's Draft & Save tab (browser), or a markdown inbox workflow (`notes-inbox/` → `import_notes.py`) for capturing notes from the terminal/Claude Code without context-switching
- Deployable to the cloud — Docker web service on Render via `render.yaml`, with the Postgres database hosted on Neon

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
| Database | PostgreSQL 15 (local Docker) / 18 (Neon, prod) |
| Vector search | pgvector (0.8.0 local / 0.8.1 Neon) |
| ORM | SQLAlchemy 2.x (async) |
| Schemas | Pydantic v2 |
| Migrations | Alembic |
| Environment | Docker Compose |
| Testing | pytest + httpx |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | Anthropic Claude (Haiku 4.5) |
| MCP | Model Context Protocol SDK (`mcp>=1.28.0`) — local stdio server (low-level `Server`) |
| Web UI | Plain HTML + fetch() (no framework) |
| Cloud | Render (web service) + Neon (Postgres) |

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
LearnStack runs on [Render](https://render.com). `render.yaml` defines the web service as code; `GET /health` supports Render's health check. (At the time, Render also provisioned a managed Postgres database — that database later moved to Neon in Phase 14.)

### Phase 11 — Notes Assistant ✓
`POST /chat` runs a multi-tool agent loop (`tool_choice: "auto"`) over `search_notes` and `create_note`, deciding per turn whether to search your notes, draft a new one, or just reply. Drafts are confirm-before-save — returned for review, never auto-persisted. New **Assistant** chat tab in the web UI. 34 passing tests (7 new).

### Phase 12 — Continuous integration ✓
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs the full test suite against a `pgvector/pgvector:pg15` service container on every pull request and push to `main`. The suite mocks the embedding seam and the LLM clients, so CI needs **no API keys and makes no live calls**. A branch-protection rule on `main` requires the CI check to pass before merge — the gate in front of Render's auto-deploy.

### Phase 13 — Logging ✓
Deliberate, leveled logging across the app's boundaries — the OpenAI/Anthropic call seams and note create/update/delete plus semantic search — driven by a `LOG_LEVEL` env var so the deployed app is observable on Render. Log lines carry a timestamp, the emitting module, and a level; never API keys, embedding vectors, or note content. See [Logging](#logging) below.

### Phase 14 — Neon database migration ✓
Moved the production Postgres database from Render's expiring free tier to [Neon](https://neon.tech) (free tier, with `pgvector`); the web service stays on Render. `app/database.py` and `alembic/env.py` share `split_ssl_args()`, which strips Neon's libpq-only `sslmode`/`channel_binding` params and passes SSL via asyncpg's `connect_args` — a no-op for the local/CI URL. `render.yaml` no longer provisions a database. Existing notes copied across with `pg_dump`/`pg_restore`. See [Cloud deployment](#cloud-deployment-render--neon) below.

### Phase 15 — Local MCP server ✓
A local (stdio) [Model Context Protocol](https://modelcontextprotocol.io) server (`app/mcp_server.py`) exposes LearnStack's notes tools to any MCP host (Claude Code, Claude Desktop): **`search_notes`** (semantic search) and **`create_note`** (a *staged* write). `create_note` inserts into a new `pending_notes` table — it never writes `notes` directly and never embeds. Staged notes are reviewed, edited, and approved in a new **Pending** tab in the web UI; approval promotes the note into `notes` via the existing write path (embedding the final text) and deletes the pending row. Pointed at `DATABASE_URL=<Neon>`, the server captures into the system-of-record database behind that human review gate. Built on the low-level `mcp.server.Server` so the tool schema/prose is reused verbatim from the existing Anthropic tools. 48 passing tests (14 new). See [MCP server](#mcp-server-claude-code--claude-desktop) below.

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

> **macOS / Linux:** `setup.ps1` is Windows PowerShell only (a `setup.sh` is a future addition). Run the same seven steps by hand: `docker compose up -d` → create and activate a venv (`python -m venv .venv && source .venv/bin/activate`) → `pip install -r requirements.txt` → `cp .env.example .env` and fill in your API keys → `alembic upgrade head` → create the test database (`createdb learnstack_test` and `CREATE EXTENSION IF NOT EXISTS vector` in it, or use `docker exec`) → `uvicorn app.main:app --reload`.

### API keys required

| Key | Used for |
|---|---|
| `OPENAI_API_KEY` | Embedding pipeline — note create/update, semantic search |
| `ANTHROPIC_API_KEY` | `/ask` (RAG answers), `/draft` (note drafting), and `/chat` (notes assistant) |

Set both in `.env` before re-running `.\setup.ps1`. The app starts without them but embedding and LLM features will error.

### Running tests

```powershell
pytest
```

The test database is created automatically by `setup.ps1`. If you ever destroy volumes with `docker compose down -v`, re-run `.\setup.ps1` to recreate it.

Tests run without any API keys and make no live calls: an autouse fixture in `tests/conftest.py` patches the OpenAI embedding call with a deterministic stand-in, and the LLM-backed tests mock their Anthropic clients. The whole suite runs on every PR — no tests are skipped. The semantic-ranking test injects controlled vectors so it verifies the ordering and scoring logic deterministically, rather than depending on a live model.

### Continuous integration

Every pull request and push to `main` triggers `.github/workflows/ci.yml`, which runs `pytest` on Linux against a `pgvector/pgvector:pg15` service container — matching the deploy target and catching environment-specific breakage before Render does. Because the suite mocks all external API calls, CI requires no secrets. A branch-protection rule on `main` requires this check to pass before merge.

### Logging

Logging verbosity is controlled by the `LOG_LEVEL` env var (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; defaults to `INFO`, and an unrecognized value falls back to `INFO` rather than crashing startup). Each line carries a timestamp, the emitting module, and the level — e.g. `2026-06-21 12:00:00 INFO app.crud.notes: Created note <id> (type=...)`.

The level convention:

| Level | Used for | Examples |
|---|---|---|
| `DEBUG` | High-frequency internal detail, off in production | per-call embedding requests (size only) |
| `INFO` | Discrete operations and state changes | note created/updated/deleted, `/ask` and `/draft` calls, each `/chat` agent-loop iteration, search returned N |
| `WARNING` | Recoverable oddities | a semantic search returning zero notes, the `/chat` iteration cap |
| `ERROR` / `exception` | Failures | an embedding or model call that raised |

Logs never include API keys, embedding vectors, or note content — only ids, changed field names, sizes, and counts. On Render, set `LOG_LEVEL` in `render.yaml` (committed as a non-secret default) and redeploy to change verbosity.

### MCP server (Claude Code + Claude Desktop)

LearnStack ships a local [Model Context Protocol](https://modelcontextprotocol.io) server (`app/mcp_server.py`) that exposes your notes tools to any MCP host — Claude Code, Claude Desktop — over stdio:

- **`search_notes`** — semantic search over your notes (embeds the query, needs `OPENAI_API_KEY`).
- **`create_note`** — a **staged** write: it inserts into the `pending_notes` table and does *not* embed. The staged note is reviewed, edited, and approved in the web UI's **Pending** tab; only on approval is it embedded and promoted into `notes`. Nothing an MCP host captures reaches your knowledge base without that human checkpoint.

The server connects to whatever `DATABASE_URL` is set in its process environment. To capture into your **system-of-record (Neon)** notes, launch it with `DATABASE_URL` = your Neon connection string. Because `app/database.py` calls `load_dotenv(override=False)`, a `DATABASE_URL` provided in the host's env block **wins over the repo `.env`** — so the MCP server talks to Neon while your local web app and tests keep using the Docker `.env`. **Do not** point the repo `.env` at Neon (that would send local dev and `pytest` to production); set Neon only in the MCP server's own launch env.

> **Prerequisite for `create_note` against Neon:** the `pending_notes` table must exist in Neon. It is created by the startup migration (`alembic upgrade head`) on the next Render deploy after this phase merges to `main`. `search_notes` works against Neon immediately (the `notes` table already exists).

#### Claude Code (VS Code CLI and chat share one config)

Register at **local scope** (stored in `~/.claude.json`, private to you — nothing is committed). Substitute your Neon URL, OpenAI key, and venv path:

```powershell
claude mcp add-json learnstack '{"command":"C:/Projects/learn-stack/.venv/Scripts/python.exe","args":["-m","app.mcp_server"],"env":{"DATABASE_URL":"<NEON_URL>","OPENAI_API_KEY":"<OPENAI_KEY>","PYTHONPATH":"C:/Projects/learn-stack"}}'
```

> Why `add-json` and not `claude mcp add … -- python -m app.mcp_server`? The plain `add` command's parser treats the `-m` as its own flag and errors; passing the config as a JSON blob sidesteps that. Local scope is the default for `add-json`.

#### Claude Desktop

Add an `mcpServers` entry to `%APPDATA%\Claude\claude_desktop_config.json` (create the key if it doesn't exist), then fully quit and reopen Claude Desktop:

```json
{
  "mcpServers": {
    "learnstack": {
      "command": "C:/Projects/learn-stack/.venv/Scripts/python.exe",
      "args": ["-m", "app.mcp_server"],
      "env": {
        "DATABASE_URL": "<NEON_URL>",
        "OPENAI_API_KEY": "<OPENAI_KEY>",
        "PYTHONPATH": "C:/Projects/learn-stack"
      }
    }
  }
}
```

Use the same Neon string you gave Render (scheme `postgresql+asyncpg://…`, keep the `?sslmode=…&channel_binding=…` params — the app strips them at runtime). `PYTHONPATH` lets `-m app.mcp_server` import the `app` package regardless of the host's working directory.

Then, from the host, ask it to capture a note — e.g. *"save a LearnStack note about the Neon SSL gotcha"*. It calls `create_note`, which stages the note; review and approve it in the **Pending** tab of the app instance pointed at the same database (the deployed Render app for Neon, or a local app run with `DATABASE_URL=<Neon>`).

- The server is a **subprocess of the host**: it starts when the host connects and shuts down when you exit — nothing keeps listening afterward.
- stdio uses **stdout** for the JSON-RPC protocol, so the server logs to **stderr**.
- Neon autosuspends on idle, so the first tool call after a quiet period is slow (~1–3s wake); `pool_pre_ping` keeps it from erroring on a dropped connection.

---

## Cloud deployment (Render + Neon)

LearnStack runs as a Docker web service on [Render](https://render.com), backed by a [Neon](https://neon.tech) Postgres database (free tier, with `pgvector`). The web service config lives in `render.yaml`; the database is hosted on Neon and connected via the `DATABASE_URL` secret. (Earlier the database was Render-managed; it was moved to Neon because Render's free Postgres suspends after 30 days — see the migration notes in `CLAUDE.md`, Phase 14.)

> **Render and Neon are the hosts this project happens to use, not requirements.** The only hard dependencies are **Postgres with the `pgvector` extension** and an async connection via the `postgresql+asyncpg://` scheme — any provider that offers those works (Supabase, Render Postgres, AWS RDS, a self-hosted instance, etc.), as does any Docker-capable web host in place of Render. The connection handling is provider-agnostic: `split_ssl_args` in `app/database.py` strips libpq-only SSL params (`sslmode`, `channel_binding`) from *any* URL that carries them and is a no-op otherwise, so a different host's connection string needs no code change. The steps below use Neon + Render as a concrete, worked example — substitute your own and the walkthrough still applies. (The embedding and LLM providers — OpenAI and Anthropic — *are* wired into the code and are not swappable without changes.)

### First deploy

1. Push the repo to GitHub.
2. Create a Neon project (plain Postgres — no add-ons needed). Copy the **direct** (non-pooler) connection string from Neon's Connect panel; it looks like `postgresql://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/DBNAME?sslmode=require&channel_binding=require`. Pick a Neon region close to your Render region to minimize latency.
3. In the Render dashboard: **New → Blueprint** → connect your repo. Render reads `render.yaml` and creates the web service (no database — Render does not provision one).
4. On the **learnstack** web service → **Environment** tab, set the three secrets: `DATABASE_URL` = the Neon string with the scheme changed from `postgresql://` to `postgresql+asyncpg://` (leave the `?sslmode=...&channel_binding=...` params in place — the app strips them at runtime; see `app/database.py`), plus `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.
5. Deploy — Alembic migrations run automatically on startup, creating the schema and the `pgvector` extension on Neon.
6. The app is live at your Render-assigned URL.

### Subsequent deploys

Push to the connected branch — Render rebuilds and redeploys automatically. Migrations run on every startup and are idempotent — if the schema is already current, they complete instantly with no changes.

### Why migrations run on startup

`Dockerfile.app` runs `alembic upgrade head` before starting uvicorn, ensuring
the schema is always in sync with the codebase on deploy. This is safe because
Alembic migrations are idempotent. (Note: Neon provides a SQL console for manual
intervention if needed, but startup migration remains the primary mechanism.)

### Loading notes into the cloud database (Neon)

`pg_dump` and `pg_restore` are not installed locally — Postgres runs inside Docker, so these commands run via `docker exec`. The destination is Neon's connection string (use the plain `postgresql://...` form here, **not** the `+asyncpg` SQLAlchemy variant — `pg_dump`/`pg_restore` are libpq tools and understand `sslmode`/`channel_binding` natively).

> The container is named `learn-stack-db-1` below — Docker Compose derives that from the project (folder) name, so if you cloned into a differently-named directory yours will differ. Run `docker ps` to get the actual name and substitute it in the commands.

```powershell
# Dump the notes table from local Docker Postgres (schema + data, custom format)
docker exec -t learn-stack-db-1 pg_dump -U postgres -d learnstack -F c -t notes -f /tmp/notes.dump
docker cp learn-stack-db-1:/tmp/notes.dump ./notes.dump

# Restore DATA ONLY into Neon (schema already created by the startup migration)
docker cp notes.dump learn-stack-db-1:/tmp/notes.dump
docker exec -t learn-stack-db-1 pg_restore --no-owner --data-only -t notes -F c -d "postgresql://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/DBNAME?sslmode=require" /tmp/notes.dump

# Clean up the temp dump files
docker exec learn-stack-db-1 rm /tmp/notes.dump
rm ./notes.dump
```

`--data-only -t notes` copies only the note rows — the `notes` table and `pgvector` extension already exist on Neon from the startup migration (which must have run at least once first). Duplicate-key errors on rows that already exist are safe to ignore. Verify the copy with `pg_restore`'s libpq URL:

```powershell
docker exec -t learn-stack-db-1 psql "postgresql://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/DBNAME?sslmode=require" -c "select count(*) from notes;"
```

---

## Inspiration

This project was inspired by Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept — the idea of a persistent, AI-maintained personal knowledge base where knowledge compounds over time rather than scattering across chat history. The YouTube video [*Build An AI Second Brain Knowledge Base (Step-By-Step)*](https://www.youtube.com/watch?v=yke4fLQUsh4) helped bring that concept into focus.

The architecture here takes a different approach: rather than an LLM-maintained wiki, LearnStack is a RAG system — you write the notes, they get embedded, and the system retrieves and answers from what you actually captured. The implementation is my own, built incrementally over fifteen phases as a learning exercise in FastAPI, Postgres, pgvector, LLM API integration, agent loops, MCP servers, and cloud deployment.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.