# Phase 3 — pgvector setup (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 3 — Complete ✓

**Goal:** Add the pgvector Postgres extension and an `embedding` column to the notes table via Alembic migration. No Python application changes yet — just learning how Postgres extensions work and how to add a column to an existing table safely. ✓

Built:
- [x] Switched Docker image to a custom build with pgvector compiled from source (`Dockerfile`)
- [x] `pgvector>=0.3.0` added to `requirements.txt`
- [x] Alembic migration: `CREATE EXTENSION IF NOT EXISTS vector` + `embedding vector(1536)` column (`alembic/versions/7fd0d6c70b7f_add_pgvector_embedding_column.py`)
- [x] Migration applied — pgvector 0.8.0 active, `notes` table has `embedding` column
