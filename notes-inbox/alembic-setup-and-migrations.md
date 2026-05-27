---
type: technical_note
tool: Alembic
topic: migrations
project: learnstack
---

# Setting up Alembic for database migrations in a FastAPI project

Alembic replaces SQLAlchemy's `create_all` with versioned migration scripts that
can safely modify existing tables without dropping data.

## Installation and initialization

Add `alembic>=1.13.0` to requirements.txt, then:

```
pip install alembic
alembic init alembic
```

This creates `alembic.ini` (config file) and an `alembic/` folder containing
`env.py` (the migration environment) and a `versions/` folder for migration scripts.

## Configuration

Two files need changes after init:

**alembic.ini** — comment out the hardcoded URL line. The URL should come from
the environment, not a committed config file:
```
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

**alembic/env.py** — three things to configure:
1. Load the DATABASE_URL from the environment (use python-dotenv load_dotenv)
2. Set `target_metadata = Base.metadata` so autogenerate can inspect the models
3. Import all model modules so they register with Base.metadata

```python
from app.database import Base
import app.models.note  # noqa: F401 — must import so Note registers with Base.metadata

target_metadata = Base.metadata
```

Since the app uses asyncpg (async driver), env.py also needs async migration support:

```python
async def run_async_migrations() -> None:
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())
```

## Generating and applying migrations

Before generating the first migration, drop any tables created outside of Alembic
(e.g. from create_all) so autogenerate starts from a clean state:

```
docker exec <container> psql -U postgres -d learnstack -c "DROP TABLE IF EXISTS notes; DROP TYPE IF EXISTS notetype;"
```

Generate the migration:
```
alembic revision --autogenerate -m "create notes table"
```

Alembic compares Base.metadata (the models) against the actual database and writes
a migration script with upgrade() and downgrade() functions.

Apply it:
```
alembic upgrade head
```

`head` means apply all migrations up to the latest version.

## Remove create_all from main.py

Once Alembic owns the schema, remove `create_all` from the app startup lifespan.
Alembic runs separately — the app no longer needs to manage table creation.

## Key gotcha

If model modules are not imported in env.py before autogenerate runs, Base.metadata
is empty. Alembic sees tables in the database but no matching models, and generates
a DROP TABLE migration instead of CREATE TABLE. Always import model modules explicitly
in env.py even if nothing in the file uses them directly.

## Ongoing workflow

For every future schema change:
1. Modify the SQLAlchemy model
2. Run `alembic revision --autogenerate -m "description of change"`
3. Review the generated migration script
4. Run `alembic upgrade head`
