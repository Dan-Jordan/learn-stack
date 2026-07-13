# Phase 9 — Setup script (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
