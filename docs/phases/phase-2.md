# Phase 2 — Alembic migrations (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
