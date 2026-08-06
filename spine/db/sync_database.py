from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from spine.config.settings import settings


def sync_database_url() -> str:
    url = settings.database_url
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg2", 1)
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url


_sync_engine = None
_SyncSessionLocal: sessionmaker[Session] | None = None


def get_sync_engine():
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        _sync_engine = create_engine(sync_database_url(), pool_pre_ping=True)
        _SyncSessionLocal = sessionmaker(_sync_engine, expire_on_commit=False)
    return _sync_engine


def get_sync_session() -> Session:
    get_sync_engine()
    assert _SyncSessionLocal is not None
    return _SyncSessionLocal()
