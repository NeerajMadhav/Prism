"""Dashboard cache invalidation helpers."""

from src.config.redis_client import redis_available, redis_delete, redis_scan_delete
from src.utils.date_utils import current_month_start
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def invalidate_dashboard_cache(org_id: str, provider: str | None = None) -> None:
    """Delete Redis dashboard keys for an org after sync (no-op without Redis)."""
    if not redis_available():
        return
    month = current_month_start().strftime("%Y-%m")
    keys = [
        f"dash:{org_id}:overall:{month}",
        f"dash:{org_id}:forecast:{month}",
        f"dash:{org_id}:scorecard",
        f"unit:econ:{org_id}:{month}",
    ]
    if provider:
        keys.append(f"dash:{org_id}:{provider}:{month}")
    else:
        await redis_scan_delete(f"dash:{org_id}:*")
    await redis_delete(*keys)
    logger.info("dashboard_cache_invalidated", org_id=org_id, provider=provider, count=len(keys))
