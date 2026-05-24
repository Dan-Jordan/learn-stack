---
type: concept
tool: SQLAlchemy
topic: ORM
project: learnstack
---

# SQLAlchemy session is a unit of work, not a connection

A Session tracks changes to ORM objects in memory and flushes them to the
database as one transaction when you call commit(). It is not the same as
holding open a database connection.

In FastAPI you yield one session per request and close it when the request
finishes. This keeps transactions short and avoids connection leaks.

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

The session is injected into route handlers via FastAPI's Depends() system.
