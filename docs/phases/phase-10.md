# Phase 10 — Cloud deployment (Render) (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
