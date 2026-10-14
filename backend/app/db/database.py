"""Async SQLAlchemy. SQLite locally (aiosqlite), Postgres in production
(asyncpg, e.g. Neon or Supabase): same code, different DATABASE_URL."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_sessions: async_sessionmaker[AsyncSession] | None = None

# libpq query parameters that asyncpg does not understand.
_DROP_PARAMS = {"channel_binding", "sslcert", "sslkey", "sslrootcert", "options"}


def normalize_database_url(url: str) -> tuple[str, dict]:
    """Turn the URL a provider hands out (Neon, Supabase: libpq style) into
    what SQLAlchemy + asyncpg accept. Returns (url, connect_args)."""
    if url.startswith("sqlite"):
        return url, {}
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    params = dict(parse_qsl(parts.query))
    connect_args: dict = {}
    sslmode = params.pop("sslmode", None)
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = "require"
    for key in _DROP_PARAMS:
        params.pop(key, None)
    if "-pooler" in parts.hostname or "pgbouncer" in url:
        # PgBouncer in transaction mode can't track asyncpg's prepared statements.
        connect_args["statement_cache_size"] = 0
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(params), parts.fragment)), connect_args


def get_engine() -> AsyncEngine:
    global _engine, _sessions
    if _engine is None:
        url, connect_args = normalize_database_url(get_settings().db_url)
        if url.startswith("sqlite"):
            Path(url.split("///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)
            _engine = create_async_engine(url, connect_args={"check_same_thread": False})
        else:
            _engine = create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)
        _sessions = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessions is not None
    return _sessions


def _sync_schema(conn) -> None:
    """create_all for new tables, then add any column (and its indexes) that a
    newer model declares but an existing table lacks. Enough while the schema
    only grows; a destructive change needs a real migration."""
    Base.metadata.create_all(conn)
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column.type.compile(conn.dialect)}"
            if not column.nullable:
                default = column.default.arg if column.default is not None else None
                if default is None or callable(default):
                    raise RuntimeError(f"{table.name}.{column.name}: a NOT NULL column needs a literal default")
                literal = f"'{default}'" if isinstance(default, str) else str(default)
                ddl += f" NOT NULL DEFAULT {literal}"
            conn.execute(text(ddl))
        for index in table.indexes:
            index.create(conn, checkfirst=True)


async def init_db() -> None:
    """Create or extend the schema. Over a direct (unpooled) connection when
    the provider gives one: PgBouncer's transaction mode and DDL don't mix."""
    from . import models  # noqa: F401  (registers the tables on Base)

    settings = get_settings()
    if settings.database_url_unpooled and not settings.db_url.startswith("sqlite"):
        url, connect_args = normalize_database_url(settings.database_url_unpooled)
        ddl_engine = create_async_engine(url, connect_args=connect_args)
        try:
            async with ddl_engine.begin() as conn:
                await conn.run_sync(_sync_schema)
        finally:
            await ddl_engine.dispose()
        return
    async with get_engine().begin() as conn:
        await conn.run_sync(_sync_schema)


async def dispose_db() -> None:
    global _engine, _sessions
    if _engine is not None:
        await _engine.dispose()
    _engine = _sessions = None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
