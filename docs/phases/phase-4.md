# Phase 4 — Embedding pipeline (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 4 — Complete ✓

**Goal:** Generate and store vector embeddings for notes automatically on create and update. ✓

Built:
- [x] `openai>=1.0.0` added to `requirements.txt`
- [x] `OPENAI_API_KEY` added to `.env.example`
- [x] `app/embeddings.py` — async helper calling `text-embedding-3-small`, returns 1536 floats
- [x] `app/models/note.py` — `embedding` column added to ORM model using `pgvector.sqlalchemy.Vector(1536)`
- [x] `app/crud/notes.py` — `create_note` embeds on create; `update_note` re-embeds only when `content` changes
