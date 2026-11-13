"""Async Redis client — optional. API works with DB alone when Redis is down."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_redis: redis.Redis | None = None
_redis_available: bool = False


async def init_redis() -> redis.Redis | None:
    """Connect to Redis if configured; never fail app startup when unavailable."""
    global _redis, _redis_available
    settings = get_settings()
    url = (settings.redis_url or "").strip()
    if not url:
        logger.warning("redis_disabled", reason="REDIS_URL empty")
        _redis = None
        _redis_available = False
        return None

    client = redis.from_url(
        url,
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        await client.ping()
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))
        try:
            await client.aclose()
        except Exception as close_exc:
            logger.debug("redis_close_failed", error=str(close_exc))
        _redis = None
        _redis_available = False
        return None

    _redis = client
    _redis_available = True
    logger.info("redis_connected")
    return _redis


async def close_redis() -> None:
    """Close the global Redis client if open."""
    global _redis, _redis_available
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as close_exc:
            logger.debug("redis_close_failed", error=str(close_exc))
        _redis = None
    _redis_available = False


def redis_available() -> bool:
    """True when Redis was initialized and last known reachable."""
    return _redis_available and _redis is not None


def get_redis_client() -> redis.Redis | None:
    """Return Redis client or None when unavailable (callers must tolerate None)."""
    return _redis if _redis_available else None


async def get_redis() -> AsyncIterator[redis.Redis | None]:
    """Yield Redis client for a request (may be None)."""
    yield get_redis_client()


async def redis_get(key: str) -> str | None:
    """Safe GET — returns None if Redis is down."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        logger.warning("redis_get_failed", key=key[:48], error=str(exc))
        return None


async def redis_set(key: str, value: str, *, ex: int | None = None) -> bool:
    """Safe SET — returns False if Redis is down."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        await client.set(key, value, ex=ex)
        return True
    except Exception as exc:
        logger.warning("redis_set_failed", key=key[:48], error=str(exc))
        return False


async def redis_delete(*keys: str) -> None:
    """Safe DELETE — no-op if Redis is down."""
    client = get_redis_client()
    if client is None or not keys:
        return
    try:
        await client.delete(*keys)
    except Exception as exc:
        logger.warning("redis_delete_failed", error=str(exc))


async def redis_incr(key: str, *, expire_seconds: int | None = None) -> int | None:
    """Safe INCR — returns None if Redis is down (caller should skip limit)."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        count = int(await client.incr(key))
        if count == 1 and expire_seconds:
            await client.expire(key, expire_seconds)
        return count
    except Exception as exc:
        logger.warning("redis_incr_failed", key=key[:48], error=str(exc))
        return None


async def redis_scan_delete(match: str) -> int:
    """Delete keys matching pattern; returns count deleted (0 if Redis down)."""
    client = get_redis_client()
    if client is None:
        return 0
    try:
        keys: list[Any] = []
        async for key in client.scan_iter(match=match):
            keys.append(key)
        if keys:
            await client.delete(*keys)
        return len(keys)
    except Exception as exc:
        logger.warning("redis_scan_delete_failed", match=match, error=str(exc))
        return 0
