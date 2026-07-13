# Phase 11 — Notes Assistant (/chat agent loop) (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

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
