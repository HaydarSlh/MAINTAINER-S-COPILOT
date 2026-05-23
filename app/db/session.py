"""Async SQLAlchemy engine + session factory.

The DB password is resolved from Vault at startup (app/infra/vault.py) — it is
never read from .env or hardcoded. Only repositories use sessions; services own
the transaction boundary, the API layer never touches a session.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.infra.vault import read_secret


@lru_cache(maxsize=1)
def _engine():
    """Build the async engine once, cached for the process lifetime."""
    creds = read_secret("secret/data/db")
    user = creds["username"]
    password = creds["password"]
    url = (
        f"postgresql+asyncpg://{user}:{password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )
    return create_async_engine(url, echo=False, pool_pre_ping=True)


def get_engine():
    return _engine()


_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a session.

    Used as `async with get_session() as session:`. Callers own the transaction
    boundary via `async with session.begin()`; the session is closed on exit.
    """
    factory = _get_factory()
    async with factory() as session:
        yield session
