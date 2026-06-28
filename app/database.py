import os
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


def split_ssl_args(url: str) -> tuple[str, dict]:
    """Move libpq-only TLS params out of the URL and into asyncpg connect_args.

    Neon's connection string carries ``?sslmode=require`` (and often
    ``&channel_binding=require``). These are libpq/psycopg parameters that
    asyncpg does not understand — leaving them in the URL raises a connection
    error. We strip them and, if SSL was requested, pass it explicitly via
    ``connect_args={"ssl": True}``.

    For the local Docker URL (no ``sslmode``) this is a no-op: the query stays
    empty and ``connect_args`` comes back empty, so behavior is unchanged.

    Shared with ``alembic/env.py`` so the migration engine and the app engine
    handle Neon's URL identically — both connection paths must stay in sync.
    """
    split = urlsplit(url)
    query = dict(parse_qsl(split.query))

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # also libpq-only; asyncpg rejects it

    connect_args: dict = {}
    if sslmode is not None and sslmode != "disable":
        connect_args["ssl"] = True

    cleaned = urlunsplit(split._replace(query=urlencode(query)))
    return cleaned, connect_args


DATABASE_URL, _connect_args = split_ssl_args(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
