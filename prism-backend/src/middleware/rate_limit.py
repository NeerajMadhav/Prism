"""slowapi rate limiter — Redis when available, otherwise in-memory."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Prefer Redis for multi-worker shared counters; memory:// keeps API working alone.
_redis_url = (os.environ.get("REDIS_URL") or "").strip()
_storage_uri = _redis_url if _redis_url else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300/minute"],
    storage_uri=_storage_uri,
)
