"""API remains usable when Redis is unavailable."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.config import redis_client as redis_mod


@pytest.mark.asyncio
async def test_core_api_without_redis(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    """Simulate Redis down — costs, auth, health still succeed via DB."""
    redis_mod._redis = None
    redis_mod._redis_available = False

    health = await client.get("/health")
    assert health.status_code == 200, health.text
    body = health.json()
    assert body["db"] is True
    assert body["redis"] is False
    assert body["status"] in ("ok", "degraded")

    costs = await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=auth_headers)
    assert costs.status_code == 200, costs.text
    assert costs.json()["total_usd"] > 0

    by_day = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs/by-day", headers=auth_headers
    )
    assert by_day.status_code == 200
    assert "days" in by_day.json()

    me = await client.get("/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_works_without_redis(client: AsyncClient, owner: dict) -> None:
    redis_mod._redis = None
    redis_mod._redis_available = False

    forgot = await client.post(
        "/v1/auth/forgot-password", json={"email": owner["email"]}
    )
    assert forgot.status_code == 200

    from src.config.database import get_pool
    from src.utils.security import hash_password

    pool = get_pool()
    raw = "reset-token-without-redis-123456"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET password_reset_token = $1,
                password_reset_expires = NOW() + INTERVAL '1 hour'
            WHERE id = $2
            """,
            hash_password(raw),
            owner["user_id"],
        )

    reset = await client.post(
        "/v1/auth/reset-password",
        json={
            "user_id": str(owner["user_id"]),
            "token": raw,
            "new_password": "BrandNew1!",
        },
    )
    assert reset.status_code == 200, reset.text

    login = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": "BrandNew1!"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_account_create_survives_celery_down(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.workers.sync_worker.sync_account.apply_async",
        side_effect=Exception("broker down"),
    ), patch(
        "src.workers.sync_worker.run_sync_inline",
        new_callable=AsyncMock,
        return_value={"status": "success", "records": 0},
    ):
        res = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "aws",
                "display_name": "No Celery AWS",
                "scope": "account",
                "credentials": {
                    "role_arn": "arn:aws:iam::222233334444:role/Prism",
                    "external_id": "ext",
                    "region": "us-east-1",
                },
            },
        )
    assert res.status_code == 201, res.text
    assert res.json()["account_id"] == "222233334444"
    assert res.json()["sync_mode"] == "inline"
