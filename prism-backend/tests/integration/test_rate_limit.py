"""Rate limiting on auth endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import STRONG_PASSWORD


@pytest.mark.asyncio
async def test_auth_rate_limit_triggers(client: AsyncClient, enable_rate_limit) -> None:
    """Burst login attempts should eventually return 429 (10/15min per IP)."""
    statuses = []
    for i in range(15):
        res = await client.post(
            "/v1/auth/login",
            json={"email": f"ratelimit{i}@example.com", "password": STRONG_PASSWORD},
        )
        statuses.append(res.status_code)
        if res.status_code == 429:
            break
    assert 429 in statuses, f"expected rate limit 429, got {statuses}"
