# Phase 12 — Continuous integration (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 12 — Complete ✓

**Goal:** A GitHub Actions workflow runs the full test suite against real Postgres + pgvector on every pull request, and a branch-protection rule requires that check to pass before merge to `main`. ✓

**Why:** `main` auto-deploys to Render on merge (Phase 10), but nothing currently stops a broken merge from shipping — the only safeguard was remembering to run `pytest` locally on Windows. CI closes that gap and adds a Linux test run matching the deploy target, catching environment-specific breakage before Render does. First of two production-fundamentals phases (CI, then logging) taken before resuming feature work.

Built:
- [x] `.github/workflows/ci.yml` — triggers on `pull_request` and pushes to `main`; Python 3.11 with pip cache, a `pgvector/pgvector:pg15` service container (health-checked with `pg_isready`), `pip install -r requirements.txt`, `CREATE EXTENSION IF NOT EXISTS vector`, then `pytest`. No secrets configured — the suite makes no live API calls
- [x] `tests/conftest.py` — autouse `mock_embeddings` fixture patches `app.crud.notes.embed_text` (the single seam feeding both the note-write and semantic-query paths) with a deterministic stand-in, so the suite needs no `OPENAI_API_KEY`
- [x] `tests/test_query.py` — `test_semantic_query_ranking` rewritten to inject **controlled** vectors (query ≡ SQLAlchemy note → score 1.0; Docker note orthogonal → score 0.0), testing the ordering/scoring code deterministically with no live call. Every test now runs on every PR — no skips, no marker
- [x] `README.md` / `CLAUDE.md` — CI gate and the no-secrets testing approach documented
- [x] Branch-protection ruleset on `main` (GitHub settings) — requires the CI `test` check to pass and the branch to be up to date before merge; PRs required with **0 required approvals** (solo repo); deletions and force-pushes blocked. Enabled after the first green CI run on a PR

Verified: `pytest` with no keys → 34 passed, 0 skipped — the entire suite (including ranking) runs deterministically and offline. The first PR's CI run surfaced a real gap (the app required `DATABASE_URL` at import; not set in CI) — fixed in `ci.yml`, then green.

**Design decisions:**
- **Mock the embedding call rather than give CI a real `OPENAI_API_KEY`** — a merge gate must be deterministic and self-contained; a live model call can flake on model drift, network, or rate limits, and a gate that goes red for reasons unrelated to the diff trains you to ignore red. CI tests *your* code, not OpenAI's model. No secret also keeps the key out of CI entirely, consistent with `render.yaml`'s `sync: false` posture. The discovery that drove this: contrary to the original plan's assumption, most of the suite (`test_notes`, `test_query`, `test_ask`) made **live** embedding calls — it was never actually mocked
- **One autouse fixture patching a single seam (`embed_text`)** — both the write path and the query path funnel through it, so one patch neutralizes every live call. The stub is content-derived (deterministic per text) with non-negative components, which keeps cosine distance in `[0, 1]` and similarity scores in the `[0, 1]` range the tests assert
- **Ranking test uses controlled vectors, not the real API** — `test_semantic_query_ranking` asserts that the closest vector ranks first with the right score. The thing worth testing is *LearnStack's* ordering/scoring code, which is deterministic; *OpenAI's* semantic quality is its own concern and isn't LearnStack's to test. By injecting known vectors the test runs in CI on every PR with no key — rather than a `skipif`-gated live test that silently never runs (pytest doesn't load `.env`, so it would skip even locally). If a live smoke check of real embeddings is ever wanted, the right home is a separate scheduled workflow with a secret, not a test in the merge gate — deferred as over-engineering at personal scale
- **Prebuilt `pgvector/pgvector:pg15` service container** — avoids compiling pgvector from source the way the local `Dockerfile` does, so runs stay fast
- **`create_all`, not Alembic, in CI** — `conftest.py` builds the schema directly from the ORM models, so CI only needs the `vector` extension present (the service container creates the database via `POSTGRES_DB`); no migration step is required for the test run
- **Gate covers `pytest` only** — linting / type-checking are a deliberate later addition, not part of this phase

**Risks / gotchas (carried forward):**
- Branch protection on a solo repo can block your own merges if misconfigured — enabled only after a green PR run, and configured safely: **Required approvals: 0** (GitHub won't let you approve your own PR, so ≥1 would lock you out), with admin bypass left available as an escape hatch
- The app reads `DATABASE_URL` at import time, so CI must set it even though tests override the DB session — logged as a Follow-up (lazy engine init would remove the requirement)
