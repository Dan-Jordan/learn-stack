# Phase 14 — Neon database migration (Complete)

> Archived verbatim from `CLAUDE.md` on 2026-07-10. Cross-references to other
> sections ("see the ... section below/above", "this file's ...") refer to
> CLAUDE.md as it stood at archive time. The durable record of this phase —
> decisions, gotchas, follow-ups — lives in CLAUDE.md's Decisions log and
> Follow-ups tables; this file is the full narrative.

---

## Phase 14 — Complete ✓ (Neon database migration)

**Goal:** Move the production Postgres database off Render's free tier onto Neon's free tier, with no loss of notes and no change to local dev, tests, or CI. The web service stays on Render; only the database moves. Done when the deployed app on Render reads and writes against Neon, the existing notes have been migrated across, and `render.yaml` no longer provisions a Render database.

**Why:** Render's free Postgres instance is suspended after 30 days, so the database needs a new home regardless. Neon's free tier is genuinely free (not time-boxed), speaks standard Postgres, and — critically — supports `pgvector`, which the entire RAG stack depends on. Keeping the web service on Render and moving only the database to Neon is the smallest change that solves the expiry. (Supabase is the comparable free + pgvector alternative; Neon is a fine choice and not worth overthinking.)

**This is its own phase, not part of Insights.** It is time-sensitive (gated by Render's suspension date, whereas Insights is unhurried feature work) and a different concern (deployment/infrastructure, not clustering). Bundling an SSL/connection change with a KMeans feature into one PR would be hard to review and hard to roll back — so it stays a single coherent change, consistent with the one-phase-one-concern convention. Whether it carries a phase number is cosmetic; numbering it Phase 14 (and pushing Insights to 15) keeps the two unbundled, which is the point.

**Blast radius is small — production connection only.** Local dev, the test suite, and CI all use the Docker / CI `pgvector` container, not the cloud database, so they are untouched. No business logic moves — only the two database *connection* paths (`app/database.py` and `alembic/env.py`) plus `render.yaml`; this is a connection-string and config change plus a one-time data copy.

Built:
- [x] `app/database.py` — `split_ssl_args()` moves Neon's libpq-only TLS params out of the URL and into asyncpg's `connect_args`. It strips **both** `sslmode` *and* `channel_binding` (Neon's copy-paste string carries both; asyncpg rejects both), and passes `connect_args={"ssl": True}` when SSL was requested. For the local Docker URL (no `sslmode`) it is a no-op: query stays empty, `connect_args` comes back `{}`, behavior unchanged — so local dev, tests, and CI are untouched
- [x] `alembic/env.py` — the migration engine calls the **same** `split_ssl_args()` (imported from `app.database`). This was the first-deploy fix: `env.py` built its own engine straight from `DATABASE_URL`, bypassing the helper, so `alembic upgrade head` crashed on the `sslmode` param before the app started even though the app engine was already fixed. Both connection paths now share one helper and can't drift
- [x] `render.yaml` — `databases:` block removed (Render no longer provisions the database). `DATABASE_URL` stays a `sync: false` dashboard secret; the Neon connection string (scheme `postgresql+asyncpg://`, params stripped at runtime by the code above) is pasted into the Render Environment tab
- [x] Neon project created (`learnstack`, Postgres 18.4, AWS us-west-2 / Oregon — co-located with the Render web service to minimize cross-DC latency). The **direct** (non-pooler) endpoint is used. `pgvector` 0.8.1, installed by the startup migration's `CREATE EXTENSION IF NOT EXISTS vector`
- [x] Render redeploy against Neon — live. Deployed via merge to `main` (auto-deploy) with the SSL fix in place, after the `DATABASE_URL` secret had been staged with "Save only". (The Neon password was rotated mid-migration after being shared during setup; the new value was set in Render before the successful deploy.)
- [x] Data migration — existing notes copied from local Docker Postgres into Neon with `pg_dump -t notes` → `pg_restore --data-only -t notes` (the startup migration created the schema first)
- [x] `README.md` / `CLAUDE.md` — deployment docs, phase list, and tech-stack tables point the database at Neon; decisions and gotchas recorded in the decisions log
- [x] `notes-inbox/` — the connection gotchas captured as notes (asyncpg can't parse `sslmode`/`channel_binding`; direct vs pooler endpoint; deploy ordering), imported to the notes DB

Verified: locally against live Neon before deploy — connecting through `app.database` succeeds; engine receives `...neon.tech/neondb` (no `sslmode`/`channel_binding`) with `connect_args={'ssl': True}`; server reports PostgreSQL 18.4; `pgvector` 0.8.1. After the `env.py` fix, `alembic upgrade head` against Neon cleared the `sslmode` parse and reached real authentication. Installed driver versions: SQLAlchemy 2.0.50, asyncpg 0.31.0 — `connect_args={"ssl": True}` is the correct form for these. Full suite stays green (34 passed) — the change is a no-op for the no-SSL local/CI URL.

**Design decisions:**
- **Move only the database, keep the web service on Render** — the web service free tier is not expiring; the database is. The smallest change that fixes the actual problem
- **Neon over staying on Render / over Supabase** — Render's free Postgres is the thing expiring, so staying isn't an option. Neon is picked over Supabase only on simplicity-of-fit; both are free with pgvector. Not worth deeper evaluation at personal scale
- **Declined Neon's add-ons (Neon Auth / "Backend Services", `neonctl init` AI tooling)** — Neon Auth is a multi-user identity system (users/sessions tables, OAuth); the project's upcoming Authentication phase is deliberately single-user HTTP Basic Auth, and multi-user is explicitly not planned. Adopting it would also couple the app to a Neon-specific product, cutting against this phase's whole point (staying DB-agnostic so the next move is cheap). Created a plain Postgres project, nothing else
- **Direct endpoint over the pooler** — avoids the asyncpg-prepared-statements-vs-PgBouncer problem entirely for a single low-traffic service, rather than carrying a `statement_cache_size=0` workaround for pooling the app doesn't need
- **SSL via `connect_args`, both `sslmode` and `channel_binding` stripped from the URL** — asyncpg's TLS is configured through the driver (`connect_args={"ssl": True}`), not libpq URL params. Neon's copy-paste string carries *both* `sslmode=require` and `channel_binding=require`, and asyncpg rejects both; stripping only `sslmode` would leave the second as a hidden second failure. The stripping is implemented generically (`split_ssl_args`, shared by the app engine and the Alembic migration engine) so the local URL with no such params is unaffected
- **`DATABASE_URL` stays a dashboard secret (`sync: false`)** — unchanged posture from Phase 10; the connection string (now Neon's) is still set in the Render dashboard, never committed
- **No business logic moves** — `crud/`, `routers/`, logging, and the agent loops are all DB-agnostic; this phase touches only the two DB *connection* paths (`app/database.py`, `alembic/env.py`) and `render.yaml`
- **The SSL helper is shared between the app engine and the migration engine** — the original fix only covered `app/database.py`; the first deploy crashed because `alembic/env.py` builds its own engine and bypassed it. Both now import one `split_ssl_args()` so the two connection paths handle Neon identically and can't drift. (This is the same contract-DRY principle the Phase 11 note records — share the contract, not context-tuned prose)

**Risks / gotchas:**
- **Time-sensitive** — the data copy must happen before Render suspends the instance, or the notes are gone. This is the one hard deadline in the phase
- **Deploy order matters** — the SSL-stripping fix must be on `main` *before* the live app points at Neon. Pointing the deployed (pre-fix) app at the Neon URL would crash-loop on the `sslmode` param. Mitigated by saving the Render `DATABASE_URL` with "Save only" (no deploy) and letting the merge-triggered deploy pick it up with the fix in place
- **asyncpg + `sslmode`/`channel_binding`** — the first-deploy failure mode; the URL must have both stripped and SSL passed via `connect_args` (handled by `split_ssl_args`, used by both the app and migration engines)
- **Pooler vs direct endpoint** — using the `-pooler` host with asyncpg's default prepared-statement caching causes intermittent failures; use the direct host (or `statement_cache_size=0`)
- **Cold-start latency** — Neon autosuspends on idle; the first request after a quiet period is slow (Neon takes ~1–3s to wake). Inherent and accepted on a free tier. Separately, autosuspend *drops* pooled connections, so without a liveness check that first request would also *error* (a dead connection from the pool) — handled by `pool_pre_ping=True` on the engine; see the decisions log
- **`DATABASE_URL` scheme** — must be `postgresql+asyncpg://` (not Neon's default `postgres://`), same conversion already noted for Render
