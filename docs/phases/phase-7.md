# Phase 7 — Draft agent (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
