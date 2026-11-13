"""Celery workers and async DB bridge for sync worker processes."""

from collections.abc import Awaitable, Callable

import asyncpg

from src.config.database import get_pool, init_db

_initialized = False


async def _ensure_pool() -> asyncpg.Pool:
    global _initialized
    try:
        return get_pool()
    except RuntimeError:
        await init_db()
        _initialized = True
        return get_pool()


def run_async_db[T](fn: Callable[[asyncpg.Connection], Awaitable[T]]) -> T:
    """Run an async DB callback from a sync Celery task."""
    import asyncio

    async def _runner() -> T:
        pool = await _ensure_pool()
        async with pool.acquire() as conn:
            return await fn(conn)

    return asyncio.run(_runner())
