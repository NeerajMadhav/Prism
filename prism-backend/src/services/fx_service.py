"""Foreign exchange rates with optional Redis cache."""

from __future__ import annotations

import httpx

from src.config.redis_client import redis_get, redis_set
from src.utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 6 * 60 * 60


async def get_usd_rate(currency: str) -> float:
    """Return multiplier to convert `currency` amounts to USD (6h Redis cache when available)."""
    code = (currency or "USD").upper()
    if code == "USD":
        return 1.0

    cache_key = f"fx:rate:{code}"
    cached = await redis_get(cache_key)
    if cached:
        return float(cached)

    rate = await _fetch_rate(code)
    await redis_set(cache_key, str(rate), ex=_CACHE_TTL_SECONDS)
    return rate


async def _fetch_rate(currency: str) -> float:
    """Fetch live FX from open.er-api.com (no API key required)."""
    url = f"https://open.er-api.com/v6/latest/{currency}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        usd_per_unit = float(data.get("rates", {}).get("USD", 0) or 0)
        if usd_per_unit <= 0:
            raise ValueError("invalid FX response")
        return usd_per_unit
    except Exception as exc:
        logger.error("fx_fetch_failed", currency=currency, error=str(exc))
        return 1.0
