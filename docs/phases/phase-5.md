# Phase 5 — Semantic search (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 5 — Complete ✓

**Goal:** `POST /query` accepts a question string and returns notes ranked by semantic similarity. ✓

Built:
- [x] `QueryRequest` and `QueryResult` schemas added to `app/schemas/note.py`
- [x] `search_notes_semantic` added to `app/crud/notes.py` — embeds query, runs pgvector cosine distance, filters NULL embeddings, returns `(note, score)` pairs
- [x] `app/routers/query.py` — `POST /query` endpoint, registered in `app/main.py`
- [x] `tests/test_query.py` — 6 tests: empty DB, happy path, score shape, response fields, ranking, limit

**Note:** No vector index added (ivfflat/hnsw). Not needed at personal-note scale. Add via Alembic migration if query performance degrades as the notes database grows.
