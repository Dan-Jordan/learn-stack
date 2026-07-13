# Phase 6 — LLM answer generation (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
