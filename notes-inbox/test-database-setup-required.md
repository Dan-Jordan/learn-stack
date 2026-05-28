---
type: error_fix

tool: pytest, Docker
# optional — e.g. SQLAlchemy, FastAPI, Docker, pytest

topic: testing, setup
# optional — e.g. ORM, routing, async, containers

project: learnstack
# optional — omit if not project-specific
---

# Test suite fails on fresh start — test database must be created manually

## The error

When running `pytest` against a fresh Docker Postgres container, all tests fail at setup with:

```
FATAL: database "learnstack_test" does not exist
```

## Why it happens

The Docker container creates the main `learnstack` database automatically on first start via the `POSTGRES_DB` environment variable in `docker-compose.yml`. But the test database is a separate database — nothing creates it automatically.

`conftest.py` connects to `learnstack_test`, creates tables via `Base.metadata.create_all`, runs the tests, then drops everything. It expects the database shell to already exist. It handles tables, not the database itself.

The pgvector extension is also not inherited from the main database — it must be enabled separately in `learnstack_test`, or the `embedding` column type won't be recognized.

## The fix

Run these once after starting the container for the first time:

```bash
docker exec learn-stack-db-1 psql -U postgres -c "CREATE DATABASE learnstack_test;"
docker exec learn-stack-db-1 psql -U postgres -d learnstack_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

After that, the test suite runs normally. These commands only need to be run once — the data persists in the Docker volume across restarts.

## When you'd hit this again

- Cloning the repo onto a new machine
- Running `docker compose down -v` (the `-v` flag destroys volumes, wiping all databases)
- Any other situation where the Docker volume is reset or recreated

## What to consider for the future

A `scripts/init_test_db.sh` or a `Makefile` target would make this a one-command step for new contributors (or future-you). Not urgent for a personal project, but worth noting.
