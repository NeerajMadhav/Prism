"""Accounts, costs dashboard, caps, alerts with mock cloud data."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.types.models import HealthCheckResult


@pytest.mark.asyncio
async def test_connect_aws_account_and_list(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-1", "queued"),
    ) as mock_sched:
        res = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "aws",
                "display_name": "Prod AWS",
                "scope": "account",
                "credentials": {
                    "role_arn": "arn:aws:iam::111122223333:role/PrismReadOnly",
                    "external_id": "ext-123",
                    "region": "us-east-1",
                },
            },
        )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["provider"] == "aws"
    assert body["account_id"] == "111122223333"
    assert mock_sched.called

    listed = await client.get(f"/v1/orgs/{owner['org_id']}/accounts", headers=auth_headers)
    assert listed.status_code == 200
    assert any(a["account_id"] == "111122223333" for a in listed.json())

    # credentials never returned
    assert "credentials" not in listed.json()[0]
    assert "credentials_enc" not in listed.json()[0]


@pytest.mark.asyncio
async def test_duplicate_account_409(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    payload = {
        "provider": "aws",
        "display_name": "Dup",
        "scope": "account",
        "credentials": {
            "role_arn": "arn:aws:iam::999988887777:role/Prism",
            "external_id": "ext",
            "region": "us-east-1",
        },
    }
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-dup", "queued"),
    ):
        first = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts", headers=auth_headers, json=payload
        )
        second = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts", headers=auth_headers, json=payload
        )
    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_invalid_aws_credentials_validation(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.post(
        f"/v1/orgs/{owner['org_id']}/accounts",
        headers=auth_headers,
        json={
            "provider": "aws",
            "display_name": "Bad",
            "scope": "account",
            "credentials": {"role_arn": "missing-fields"},
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_account_test_connection_mocked(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-az", "queued"),
    ):
        created = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "azure",
                "display_name": "Azure Sub",
                "scope": "subscription",
                "credentials": {
                    "tenant_id": "t1",
                    "client_id": "c1",
                    "client_secret": "s1",
                    "subscription_id": "sub-1",
                },
            },
        )
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]

    with patch("src.routers.accounts.get_connector") as mock_get:
        mock_conn = MagicMock()
        mock_conn.health_check.return_value = HealthCheckResult(ok=True)
        # health_check might be async
        async def _ok():
            return HealthCheckResult(ok=True)

        mock_conn.health_check = _ok
        mock_get.return_value = mock_conn
        # also patch sync get_usd_rate if used
        with patch("src.routers.accounts.get_usd_rate", return_value=1.0):
            # fx may be async
            async def _fx(_c="USD"):
                return 1.0

            with patch("src.routers.accounts.get_usd_rate", side_effect=_fx):
                res = await client.post(
                    f"/v1/orgs/{owner['org_id']}/accounts/{account_id}/test",
                    headers=auth_headers,
                )
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True


@pytest.mark.asyncio
async def test_costs_with_seeded_mock_data(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    overall = await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=auth_headers)
    assert overall.status_code == 200, overall.text
    data = overall.json()
    assert data.get("total_usd", 0) > 0 or "by_provider" in data
    assert data.get("granularity") == "day"
    assert data.get("billing_day_basis", "").startswith("UTC")

    by_service = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs/by-service", headers=auth_headers
    )
    assert by_service.status_code == 200

    by_day = await client.get(f"/v1/orgs/{owner['org_id']}/costs/by-day", headers=auth_headers)
    assert by_day.status_code == 200, by_day.text
    day_body = by_day.json()
    assert day_body["granularity"] == "day"
    assert day_body["billing_day_basis"].startswith("UTC")
    assert isinstance(day_body["days"], list) and len(day_body["days"]) >= 1
    assert all("date" in d and "total_usd" in d and "has_data" in d for d in day_body["days"])
    assert any(d["has_data"] and d["total_usd"] > 0 for d in day_body["days"])

    top = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs/top-services?limit=5", headers=auth_headers
    )
    assert top.status_code == 200


@pytest.mark.asyncio
async def test_create_cap_and_list(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    with patch("src.routers.caps.check_org_alerts") as mock_alerts:
        mock_alerts.delay = MagicMock()
        res = await client.post(
            f"/v1/orgs/{owner['org_id']}/caps/",
            headers=auth_headers,
            json={
                "name": "AWS Monthly",
                "scope": "platform",
                "scope_value": "aws",
                "cap_amount": 5000,
                "period": "monthly",
            },
        )
    assert res.status_code == 201, res.text
    assert mock_alerts.delay.called

    listed = await client.get(f"/v1/orgs/{owner['org_id']}/caps/", headers=auth_headers)
    assert listed.status_code == 200
    caps = listed.json()
    if isinstance(caps, dict):
        caps = caps.get("data", [])
    assert len(caps) >= 1


@pytest.mark.asyncio
async def test_alerts_list_empty_ok(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.get(f"/v1/orgs/{owner['org_id']}/alerts", headers=auth_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_org_get_put(client: AsyncClient, auth_headers: dict, owner: dict) -> None:
    got = await client.get(f"/v1/orgs/{owner['org_id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["name"] == owner["org_name"]

    put = await client.put(
        f"/v1/orgs/{owner['org_id']}",
        headers=auth_headers,
        json={"timezone": "America/New_York"},
    )
    assert put.status_code == 200
    assert put.json()["timezone"] == "America/New_York"
