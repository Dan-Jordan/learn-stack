---
type: concept
tool: SQLAlchemy
topic: async
project: learnstack
---

# create_async_engine gives you a non-blocking database connection pool

`create_async_engine` creates a pool of database connections that use Python's
`async`/`await` model. While Postgres is processing a query, Python can handle
other work — other incoming requests, other coroutines — instead of blocking
the thread waiting for a response.

This is the async counterpart to the standard `create_engine`. Use it whenever
your app is built on an ASGI framework (FastAPI, Starlette) to keep the whole
stack non-blocking.

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(DATABASE_URL)
```

The connection string must use an async driver. For PostgreSQL that means
`postgresql+asyncpg://` — not `postgresql://`.

`create_async_engine` does not open connections immediately. It creates a pool
config; actual connections are opened on first use and reused across requests.

Pair it with `async_sessionmaker` to get `AsyncSession` objects that await
every query:

```python
from sqlalchemy.ext.asyncio import async_sessionmaker

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

The practical payoff: a FastAPI app using async engine can serve many concurrent
requests with a small number of real database connections, because most of the
time spent "waiting" for Postgres is time Python can use for something else.
