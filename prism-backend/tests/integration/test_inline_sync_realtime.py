"""Prove inline sync (no Celery) writes dynamic costs and tracks sync_logs."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.config.database import get_pool
from src.types.models import ConnectorResult
from src.utils.date_utils import to_utc_day
from src.workers.sync_worker import run_sync_inline


@pytest.mark.asyncio
async def test_inline_sync_persists_costs_and_logs(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("skip-queue", "queued"),
    ):
        created = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "aws",
                "display_name": "Inline Sync AWS",
                "scope": "account",
                "credentials": {
                    "role_arn": "arn:aws:iam::555566667777:role/Prism",
                    "external_id": "inline-ext",
                    "region": "us-east-1",
                },
            },
        )
    assert created.status_code == 201, created.text
    account_id = UUID(created.json()["id"])
    org_id = owner["org_id"] if isinstance(owner["org_id"], UUID) else UUID(str(owner["org_id"]))

    day = date.today() - timedelta(days=1)
    mock_rows = [
        ConnectorResult(
            time=to_utc_day(day),
            service="Amazon EC2",
            region="us-east-1",
            cost_usd=99.5,
            cost_unblended_usd=99.5,
            cost_amortized_usd=95.0,
            tags={"env": "prod"},
            is_estimate=True,
        ),
        ConnectorResult(
            time=to_utc_day(day - timedelta(days=1)),
            service="Amazon S3",
            region="us-east-1",
            cost_usd=12.25,
            cost_unblended_usd=12.25,
            cost_amortized_usd=12.25,
            tags={},
            is_estimate=False,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.get_cost_and_usage = AsyncMock(return_value=mock_rows)
    mock_connector.get_resources = AsyncMock(return_value=[])

    with patch("src.workers.sync_worker.get_connector", return_value=mock_connector), patch(
        "src.workers.sync_worker.get_usd_rate", new_callable=AsyncMock, return_value=1.0
    ), patch("src.ws.ws_manager.ws_broadcast", new_callable=AsyncMock) as mock_ws:
        result = await run_sync_inline(account_id, org_id, backfill=False)

    assert result["status"] == "success"
    assert result["records"] == 2
    assert result["delivery"] == "inline"
    assert mock_ws.await_count >= 1

    pool = get_pool()
    async with pool.acquire() as conn:
        costs = await conn.fetchval(
            "SELECT COUNT(*) FROM cost_records WHERE account_id = $1 AND org_id = $2",
            account_id,
            org_id,
        )
        assert costs == 2
        log = await conn.fetchrow(
            """
            SELECT status, records_synced FROM sync_logs
            WHERE account_id = $1 AND org_id = $2
            ORDER BY started_at DESC LIMIT 1
            """,
            account_id,
            org_id,
        )
        assert log is not None
        assert log["status"] == "success"
        assert log["records_synced"] == 2
        acct = await conn.fetchrow(
            "SELECT last_sync_status, last_sync_records FROM cloud_accounts WHERE id = $1",
            account_id,
        )
        assert acct["last_sync_status"] == "success"
        assert acct["last_sync_records"] == 2

    # Dynamic API read of day-wise costs
    by_day = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs/by-day",
        headers=auth_headers,
    )
    assert by_day.status_code == 200, by_day.text
    days = by_day.json().get("days") or by_day.json().get("data") or []
    assert isinstance(days, list)
    total = sum(float(d.get("total_usd") or d.get("cost_usd") or 0) for d in days)
    assert total >= 111.75


@pytest.mark.asyncio
async def test_sync_endpoint_falls_back_inline_when_celery_down(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("pre", "queued"),
    ):
        created = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "aws",
                "display_name": "Fallback Sync",
                "scope": "account",
                "credentials": {
                    "role_arn": "arn:aws:iam::888899990000:role/Prism",
                    "external_id": "fb",
                    "region": "us-east-1",
                },
            },
        )
    account_id = created.json()["id"]

    with patch(
        "src.workers.sync_worker.sync_account.apply_async",
        side_effect=Exception("broker down"),
    ), patch(
        "src.workers.sync_worker.run_sync_inline",
        new_callable=AsyncMock,
        return_value={"status": "success", "records": 0},
    ):
        sync = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts/{account_id}/sync",
            headers=auth_headers,
        )
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["task_id"].startswith("inline:")
    assert "inline" in body["message"].lower()
