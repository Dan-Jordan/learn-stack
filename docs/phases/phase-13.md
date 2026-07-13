# Phase 13 — Logging (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 13 — Complete ✓

**Goal:** Deliberate, leveled logging across the app's boundaries and error paths — external API calls (OpenAI/Anthropic), database writes, and failure points — configured centrally and driven by an env var, so the running app (especially on Render) is debuggable. ✓

**Why:** Logging before this phase was a root `basicConfig` in `app/main.py` plus a single `logger.exception` in `app/assistant.py`. The rest — `crud/notes.py`, `embeddings.py`, `llm.py`, `agent.py` — was silent, so a failed embedding, an empty search, or a timed-out API call on Render left no useful trace. This phase made the deployed app observable. The emphasis was the judgment of *where* and *at what level* to log — getting the full set of considerations right, not maximizing volume.

Built:
- [x] `app/main.py` — central config: level driven by `LOG_LEVEL` (default INFO, safe fallback to INFO on an unrecognized value rather than crashing startup); format `"%(asctime)s %(levelname)s %(name)s: %(message)s"` so every line carries a timestamp + emitting module + level. Existing `httpx`→WARNING quieting kept
- [x] Per-module loggers (`getLogger(__name__)`) added to `embeddings.py`, `llm.py`, `agent.py`, `crud/notes.py`, generalizing the pattern already in `assistant.py`
- [x] External-call seams: DEBUG before the `embed_text` call (size only — fires per-write *and* per-search, too frequent for INFO) with an explicit `logger.error` on failure that carries the input size; INFO breadcrumbs before the discrete `/ask` (`generate_answer`) and `/draft` (`draft_note`) calls; INFO per `/chat` agent-loop iteration (which tools the model chose) plus a WARNING on the iteration cap
- [x] `crud/notes.py` — INFO on note create/update/delete (id and changed field names only); INFO with count on a semantic search that returns results, WARNING when it returns zero (placed in `search_notes_semantic` so `/query`, `/ask`, and `/chat` all share it)
- [x] `LOG_LEVEL` added to `.env.example` (with a comment listing valid values) and `render.yaml` (as a committed `value: INFO`, not a `sync: false` secret)
- [x] `README.md` / `CLAUDE.md` — `LOG_LEVEL` and the level convention documented

Verified: full suite stays green (34 passed). Log output was confirmed two ways without paid API calls — an isolated check that `LOG_LEVEL` toggles the DEBUG line on/off and the format renders correctly, and a targeted `pytest --log-cli-level=INFO` run showing the real `crud/notes.py` lines firing (`Created note <id> (type=...)`, `Updated note <id> (fields=['title'], re-embedded=False)`, `Semantic search returned N note(s)` / `... no notes`).

**Design decisions:**
- **`LOG_LEVEL` parsed with a safe fallback** — `getattr(logging, LOG_LEVEL.upper(), logging.INFO)` so a typo in the env var falls back to INFO instead of crashing the app on startup (a startup crash on Render is worse than a wrong level)
- **`LOG_LEVEL` is config-as-code (`value: INFO`), not a dashboard secret** — it isn't sensitive, so the default belongs in version control where it's visible and tracked; changing verbosity is a deliberate, reviewable edit-and-redeploy, unlike the `sync: false` API keys. Trade-off accepted: no dashboard-only flip without a deploy
- **Level rule, applied consistently:** DEBUG = high-frequency internal plumbing (`embed_text`) and request-shape detail; INFO = discrete user-facing operations and state changes (note create/update/delete, `/ask`, `/draft`, per-loop iteration, search-returned-N); WARNING = recoverable oddities (0 search results, iteration cap); ERROR/`exception` = failures
- **`logger.error` (re-raise) vs `logger.exception` (swallow)** — the deciding factor is whether the exception keeps propagating. If it's re-raised, log a one-line context message with `logger.error` and *no* `exc_info`, letting whoever finally handles it log the traceback (the ASGI handler, or the `/chat` loop) — this avoids duplicate tracebacks. If it's swallowed here (the agent loop's tool-dispatch `except`), use `logger.exception` because that's the only place the traceback gets captured
- **`embed_text`'s ERROR wrap earns its place by adding context, not visibility** — the failure is logged with a traceback either way (uvicorn, or the `/chat` loop). The wrap exists to carry the *input size*, which the traceback lacks and which distinguishes a token-limit failure from a transient one. Its pre-call breadcrumb is DEBUG (invisible in prod), so this is also the only embedding-specific signal at the prod level
- **Never log values** — only note ids, changed field *names*, sizes, and counts. No API keys, embedding vectors, raw note content, or question text
- **Routers deliberately left unlogged** — their only error paths are the `404` `HTTPException`s, which are expected client outcomes already recorded in uvicorn's access log; 500-class failures already get a traceback from uvicorn (or the `/chat` loop). Adding request logging would duplicate uvicorn and be exactly the cargo-cult the phase warns against

**Scope boundary:** logging only. Metrics, distributed tracing, and error-aggregation services (Sentry, OpenTelemetry) are a deliberately separate, later concern. The planned (stretch) request-correlation ID through the `/chat` loop was **not** built — deferred as over-engineering at personal scale; see Follow-ups.

**Risks / gotchas (carried forward):**
- Cargo-cult logging — a `logger.info` on every function is noise worse than silence; the value is entirely in placement and level. This drove the decision to leave the routers unlogged
- Wrong-level inflation — logging recoverable conditions as ERROR trains you to ignore ERROR (why 0-results is WARNING, not ERROR)
- Leaking secrets/PII into logs is a real production failure mode — mitigated by the never-log-values rule, but worth re-checking whenever a new log line is added
