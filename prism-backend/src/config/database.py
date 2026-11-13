"""asyncpg connection pool and FastAPI dependency."""

from collections.abc import AsyncIterator

import asyncpg

from src.config.settings import get_settings

_pool: asyncpg.Pool | None = None


async def init_db() -> asyncpg.Pool:
    """Create the global connection pool."""
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.database_pool_min,
        max_size=settings.database_pool_max,
        command_timeout=30,
        max_inactive_connection_lifetime=300,
    )
    return _pool


async def close_db() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the live pool or raise if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def get_db() -> AsyncIterator[asyncpg.Connection]:
    """Yield a pooled connection for a single request."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
