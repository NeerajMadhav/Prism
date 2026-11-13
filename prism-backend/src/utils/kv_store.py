"""Short-lived key/value: Redis preferred, Postgres app_kv fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg

from src.config.redis_client import redis_delete, redis_get, redis_set


async def kv_set(
    key: str,
    value: str,
    ttl_seconds: int,
    db: asyncpg.Connection | None = None,
) -> None:
    """Store a value with TTL. Uses Redis when up; otherwise Postgres app_kv."""
    if await redis_set(key, value, ex=ttl_seconds):
        return
    if db is None:
        raise RuntimeError("kv_set requires Redis or a DB connection")
    expires = datetime.now(tz=UTC) + timedelta(seconds=ttl_seconds)
    await db.execute(
        """
        INSERT INTO app_kv (key, value, expires_at)
        VALUES ($1, $2, $3)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at
        """,
        key,
        value,
        expires,
    )


async def kv_get(key: str, db: asyncpg.Connection | None = None) -> str | None:
    """Read a value; ignores expired Postgres rows."""
    cached = await redis_get(key)
    if cached is not None:
        return cached
    if db is None:
        return None
    row = await db.fetchrow(
        """
        SELECT value FROM app_kv
        WHERE key = $1 AND expires_at > NOW()
        """,
        key,
    )
    return row["value"] if row else None


async def kv_pop(key: str, db: asyncpg.Connection | None = None) -> str | None:
    """Get-and-delete (one-time use)."""
    cached = await redis_get(key)
    if cached is not None:
        await redis_delete(key)
        if db is not None:
            await db.execute("DELETE FROM app_kv WHERE key = $1", key)
        return cached
    if db is None:
        return None
    row = await db.fetchrow(
        """
        DELETE FROM app_kv
        WHERE key = $1 AND expires_at > NOW()
        RETURNING value
        """,
        key,
    )
    return row["value"] if row else None
