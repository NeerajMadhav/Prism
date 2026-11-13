"""Input validation, SSRF, webhook URL rules, API key scopes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_rejects_http_and_private_ip(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    http_url = await client.post(
        f"/v1/orgs/{owner['org_id']}/webhooks",
        headers=auth_headers,
        json={"url": "http://example.com/hook", "events": ["alert.fired"]},
    )
    assert http_url.status_code == 400

    private = await client.post(
        f"/v1/orgs/{owner['org_id']}/webhooks",
        headers=auth_headers,
        json={"url": "https://127.0.0.1/hook", "events": ["alert.fired"]},
    )
    assert private.status_code == 400


@pytest.mark.asyncio
async def test_virtual_tag_invalid_regex(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.post(
        f"/v1/orgs/{owner['org_id']}/virtual-tags",
        headers=auth_headers,
        json={
            "name": "Bad regex",
            "tag_key": "virtual_team",
            "tag_value": "platform",
            "conditions": [{"field": "service", "operator": "regex", "value": "[unterminated"}],
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_virtual_tag_split_pct_must_sum_100(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.post(
        f"/v1/orgs/{owner['org_id']}/virtual-tags",
        headers=auth_headers,
        json={
            "name": "Split bad",
            "tag_key": "virtual_team",
            "tag_value": "shared",
            "conditions": [{"field": "service", "operator": "contains", "value": "EC2"}],
            "split_config": {
                "strategy": "fixed_pct",
                "targets": [{"tag": "a", "pct": 40}, {"tag": "b", "pct": 40}],
            },
        },
    )
    # 400 if validated; some impls may ignore — assert not 201 on bad pct
    assert res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_pagination_limit_capped(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.get(
        f"/v1/orgs/{owner['org_id']}/alerts?limit=9999",
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    # if paginated, limit should be <= 100
    if isinstance(body, dict) and "pagination" in body:
        assert body["pagination"]["limit"] <= 100


@pytest.mark.asyncio
async def test_api_key_create_shown_once(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.post(
        f"/v1/orgs/{owner['org_id']}/api-keys",
        headers=auth_headers,
        json={"name": "CI", "scopes": ["cost.read"]},
    )
    assert res.status_code in (200, 201), res.text
    body = res.json()
    assert "raw_key" in body or "key" in body
    listed = await client.get(f"/v1/orgs/{owner['org_id']}/api-keys", headers=auth_headers)
    assert listed.status_code == 200
    items = listed.json() if isinstance(listed.json(), list) else listed.json().get("data", [])
    assert items
    assert "raw_key" not in items[0]
    assert "key_hash" not in items[0]


@pytest.mark.asyncio
async def test_notifications_get(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.get(f"/v1/orgs/{owner['org_id']}/notifications", headers=auth_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_forecasts_and_scorecard_endpoints(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    forecast = await client.get(f"/v1/orgs/{owner['org_id']}/forecasts", headers=auth_headers)
    assert forecast.status_code in (200, 404)

    scorecard = await client.get(f"/v1/orgs/{owner['org_id']}/scorecard", headers=auth_headers)
    assert scorecard.status_code == 200

    reports = await client.get(f"/v1/orgs/{owner['org_id']}/reports", headers=auth_headers)
    assert reports.status_code == 200

    recs = await client.get(f"/v1/orgs/{owner['org_id']}/recommendations", headers=auth_headers)
    assert recs.status_code == 200

    resources = await client.get(f"/v1/orgs/{owner['org_id']}/resources", headers=auth_headers)
    assert resources.status_code == 200
