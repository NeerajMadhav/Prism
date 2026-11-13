"""Remaining endpoint matrix: commitments, metrics, llm, webhooks, alerts, auth edges."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.config.database import get_pool
from src.utils.security import create_access_token
from tests.conftest import _create_verified_user


@pytest.mark.asyncio
async def test_protected_routes_require_auth(client: AsyncClient, owner: dict) -> None:
    oid = owner["org_id"]
    paths = [
        ("GET", f"/v1/orgs/{oid}"),
        ("GET", f"/v1/orgs/{oid}/costs"),
        ("GET", f"/v1/orgs/{oid}/caps/"),
        ("GET", f"/v1/orgs/{oid}/team"),
        ("GET", f"/v1/orgs/{oid}/commitments/"),
        ("GET", f"/v1/auth/me"),
    ]
    for method, path in paths:
        res = await client.request(method, path)
        assert res.status_code == 401, f"{method} {path} -> {res.status_code}"


@pytest.mark.asyncio
async def test_refresh_and_logout_cycle(client: AsyncClient, owner: dict) -> None:
    login = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": owner["password"]},
    )
    assert login.status_code == 200, login.text
    refresh = login.json()["refresh_token"]

    rotated = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["access_token"]
    new_refresh = rotated.json()["refresh_token"]

    # old refresh revoked
    reuse = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401

    out = await client.post("/v1/auth/logout", json={"refresh_token": new_refresh})
    assert out.status_code == 200


@pytest.mark.asyncio
async def test_commitments_with_mock_data(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO commitment_records
              (org_id, account_id, provider, commitment_type, resource_type,
               start_date, end_date, monthly_cost, utilization_pct, coverage_pct, status)
            VALUES
              ($1, $2, 'aws', 'savings_plan', 'ComputeSP',
               CURRENT_DATE - 30, CURRENT_DATE + 20, 500, 82.5, 70, 'active'),
              ($1, $2, 'aws', 'reserved_instance', 'm5.large',
               CURRENT_DATE - 200, CURRENT_DATE + 10, 120, 45, 40, 'expiring_soon')
            """,
            owner["org_id"],
            seeded_costs["account_id"],
        )

    listed = await client.get(
        f"/v1/orgs/{owner['org_id']}/commitments/", headers=auth_headers
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["pagination"]["total"] >= 2

    summary = await client.get(
        f"/v1/orgs/{owner['org_id']}/commitments/summary", headers=auth_headers
    )
    assert summary.status_code == 200
    assert summary.json()["total_monthly_cost"] >= 500

    expiring = await client.get(
        f"/v1/orgs/{owner['org_id']}/commitments/expiring?days=30",
        headers=auth_headers,
    )
    assert expiring.status_code == 200
    assert isinstance(expiring.json(), list)
    assert len(expiring.json()) >= 1


@pytest.mark.asyncio
async def test_business_metrics_crud_and_unit_economics(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    created = await client.post(
        f"/v1/orgs/{owner['org_id']}/metrics/",
        headers=auth_headers,
        json={"name": "Active Users", "source": "manual", "unit": "users"},
    )
    assert created.status_code == 201, created.text
    metric_id = created.json()["id"]

    dup = await client.post(
        f"/v1/orgs/{owner['org_id']}/metrics/",
        headers=auth_headers,
        json={"name": "Active Users", "source": "manual", "unit": "users"},
    )
    assert dup.status_code == 409

    today = date.today().isoformat()
    ingest = await client.post(
        f"/v1/orgs/{owner['org_id']}/metrics/{metric_id}/values",
        headers=auth_headers,
        json={"values": [{"date": today, "value": 1000}]},
    )
    assert ingest.status_code == 200, ingest.text

    values = await client.get(
        f"/v1/orgs/{owner['org_id']}/metrics/{metric_id}/values",
        headers=auth_headers,
    )
    assert values.status_code == 200

    ue = await client.get(
        f"/v1/orgs/{owner['org_id']}/metrics/unit-economics",
        headers=auth_headers,
    )
    assert ue.status_code == 200

    listed = await client.get(f"/v1/orgs/{owner['org_id']}/metrics/", headers=auth_headers)
    assert listed.status_code == 200
    assert any(m["id"] == metric_id for m in listed.json())

    deleted = await client.delete(
        f"/v1/orgs/{owner['org_id']}/metrics/{metric_id}", headers=auth_headers
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_llm_config_lifecycle(client: AsyncClient, auth_headers: dict, owner: dict) -> None:
    got = await client.get(f"/v1/orgs/{owner['org_id']}/llm/", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["api_key_set"] is False

    put = await client.put(
        f"/v1/orgs/{owner['org_id']}/llm/",
        headers=auth_headers,
        json={
            "api_key": "sk-test-key-not-real",
            "model": "openai/gpt-4o-mini",
            "monthly_budget_usd": 15,
            "is_enabled": True,
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["api_key_set"] is True
    assert put.json()["monthly_budget_usd"] == 15

    # key never returned
    again = await client.get(f"/v1/orgs/{owner['org_id']}/llm/", headers=auth_headers)
    assert "api_key" not in again.json() or again.json().get("api_key") in (None, "")

    deleted = await client.delete(f"/v1/orgs/{owner['org_id']}/llm/", headers=auth_headers)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_update_llm(
    client: AsyncClient, clean_db, owner: dict
) -> None:
    viewer = await _create_verified_user(
        clean_db,
        email="llmviewer@example.com",
        org_name="Viewer Org LLM",
        role="viewer",
        name="LLM Viewer",
    )
    # attach viewer to owner's org instead
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM team_members WHERE user_id = $1", viewer["user_id"])
        await conn.execute(
            """
            INSERT INTO team_members (org_id, user_id, role, invite_accepted)
            VALUES ($1, $2, 'viewer', TRUE)
            """,
            owner["org_id"],
            viewer["user_id"],
        )
    token = create_access_token(
        viewer["user_id"], owner["org_id"], "viewer", viewer["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.put(
        f"/v1/orgs/{owner['org_id']}/llm/",
        headers=headers,
        json={"is_enabled": True},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_webhook_create_update_delete(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    # example.com resolves publicly — allowed by SSRF guard
    created = await client.post(
        f"/v1/orgs/{owner['org_id']}/webhooks/",
        headers=auth_headers,
        json={"url": "https://example.com/hooks/prism", "events": ["alert.fired"]},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert "signing_secret" in body
    wid = body["id"]

    bad_event = await client.post(
        f"/v1/orgs/{owner['org_id']}/webhooks/",
        headers=auth_headers,
        json={"url": "https://example.com/hooks/bad", "events": ["not.real"]},
    )
    assert bad_event.status_code == 400

    updated = await client.put(
        f"/v1/orgs/{owner['org_id']}/webhooks/{wid}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert updated.status_code == 200

    listed = await client.get(f"/v1/orgs/{owner['org_id']}/webhooks/", headers=auth_headers)
    assert listed.status_code == 200
    assert any(w["id"] == wid for w in listed.json())
    assert "signing_secret" not in listed.json()[0]

    deleted = await client.delete(
        f"/v1/orgs/{owner['org_id']}/webhooks/{wid}", headers=auth_headers
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_virtual_tag_happy_path(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    created = await client.post(
        f"/v1/orgs/{owner['org_id']}/virtual-tags/",
        headers=auth_headers,
        json={
            "name": "Platform team",
            "tag_key": "virtual_team",
            "tag_value": "platform",
            "conditions": [{"field": "service", "operator": "contains", "value": "EC2"}],
        },
    )
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]

    listed = await client.get(
        f"/v1/orgs/{owner['org_id']}/virtual-tags/", headers=auth_headers
    )
    assert listed.status_code == 200
    assert any(r["id"] == rule_id for r in listed.json())

    audit = await client.get(
        f"/v1/orgs/{owner['org_id']}/virtual-tags/audit-log", headers=auth_headers
    )
    assert audit.status_code == 200

    deleted = await client.delete(
        f"/v1/orgs/{owner['org_id']}/virtual-tags/{rule_id}", headers=auth_headers
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_recommendations_status_and_resources(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        resource = await conn.fetchrow(
            """
            INSERT INTO resources
              (org_id, account_id, provider, resource_id, resource_type, name,
               region, is_idle, last_cost_usd)
            VALUES ($1, $2, 'aws', 'i-abc123', 'ec2', 'idle-box', 'us-east-1', TRUE, 40)
            RETURNING id
            """,
            owner["org_id"],
            seeded_costs["account_id"],
        )
        rec = await conn.fetchrow(
            """
            INSERT INTO recommendations
              (org_id, account_id, resource_id, type, title, description,
               savings_usd, confidence, status)
            VALUES ($1, $2, $3, 'idle_resource', 'Stop idle EC2', 'Low utilization',
                    40, 'high', 'open')
            RETURNING id
            """,
            owner["org_id"],
            seeded_costs["account_id"],
            resource["id"],
        )

    recs = await client.get(
        f"/v1/orgs/{owner['org_id']}/recommendations/", headers=auth_headers
    )
    assert recs.status_code == 200
    assert recs.json()["pagination"]["total"] >= 1

    status = await client.put(
        f"/v1/orgs/{owner['org_id']}/recommendations/{rec['id']}/status",
        headers=auth_headers,
        json={"status": "implemented"},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "implemented"

    bad = await client.put(
        f"/v1/orgs/{owner['org_id']}/recommendations/{rec['id']}/status",
        headers=auth_headers,
        json={"status": "open"},
    )
    assert bad.status_code == 400

    resources = await client.get(
        f"/v1/orgs/{owner['org_id']}/resources/", headers=auth_headers
    )
    assert resources.status_code == 200

    idle = await client.get(
        f"/v1/orgs/{owner['org_id']}/resources/idle", headers=auth_headers
    )
    assert idle.status_code == 200

    one = await client.get(
        f"/v1/orgs/{owner['org_id']}/resources/{resource['id']}",
        headers=auth_headers,
    )
    assert one.status_code == 200


@pytest.mark.asyncio
async def test_alerts_ack_snooze_and_cap_crud(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    with patch("src.routers.caps.check_org_alerts") as mock_alerts:
        mock_alerts.delay = MagicMock()
        cap = await client.post(
            f"/v1/orgs/{owner['org_id']}/caps/",
            headers=auth_headers,
            json={
                "name": "Alert Cap",
                "scope": "platform",
                "scope_value": "aws",
                "cap_amount": 50,
                "period": "monthly",
            },
        )
    assert cap.status_code == 201, cap.text
    cap_id = cap.json()["id"]

    got = await client.get(
        f"/v1/orgs/{owner['org_id']}/caps/{cap_id}", headers=auth_headers
    )
    assert got.status_code == 200

    with patch("src.routers.caps.check_org_alerts") as mock_alerts:
        mock_alerts.delay = MagicMock()
        upd = await client.put(
            f"/v1/orgs/{owner['org_id']}/caps/{cap_id}",
            headers=auth_headers,
            json={"cap_amount": 75},
        )
    assert upd.status_code == 200

    pool = get_pool()
    async with pool.acquire() as conn:
        alert = await conn.fetchrow(
            """
            INSERT INTO alerts
              (org_id, cap_id, type, scope, scope_value, severity,
               threshold_percent, message)
            VALUES ($1, $2, 'budget_threshold', 'platform', 'aws', 'warning',
                    90, 'AWS spend at 90% of cap')
            RETURNING id
            """,
            owner["org_id"],
            UUID(cap_id),
        )

    ack = await client.post(
        f"/v1/orgs/{owner['org_id']}/alerts/{alert['id']}/acknowledge",
        headers=auth_headers,
    )
    assert ack.status_code == 200, ack.text

    until = (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat()
    snooze = await client.post(
        f"/v1/orgs/{owner['org_id']}/alerts/{alert['id']}/snooze",
        headers=auth_headers,
        json={"snooze_until": until},
    )
    assert snooze.status_code == 200, snooze.text

    deleted = await client.delete(
        f"/v1/orgs/{owner['org_id']}/caps/{cap_id}", headers=auth_headers
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_account_get_sync_logs_and_delete(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-1", "queued"),
    ):
        created = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts",
            headers=auth_headers,
            json={
                "provider": "gcp",
                "display_name": "GCP Billing",
                "scope": "project",
                "credentials": {
                    "project_id": "proj-1",
                    "dataset_id": "billing_export",
                    "table_prefix": "gcp_billing_export_v1_",
                    "service_account_json": {"type": "service_account", "project_id": "proj-1"},
                },
            },
        )
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]

    got = await client.get(
        f"/v1/orgs/{owner['org_id']}/accounts/{account_id}", headers=auth_headers
    )
    assert got.status_code == 200
    assert "credentials" not in got.json()
    assert "credentials_enc" not in got.json()

    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-2", "queued"),
    ):
        sync = await client.post(
            f"/v1/orgs/{owner['org_id']}/accounts/{account_id}/sync",
            headers=auth_headers,
        )
    assert sync.status_code in (200, 202), sync.text

    logs = await client.get(
        f"/v1/orgs/{owner['org_id']}/accounts/{account_id}/sync-logs",
        headers=auth_headers,
    )
    assert logs.status_code == 200

    deleted = await client.delete(
        f"/v1/orgs/{owner['org_id']}/accounts/{account_id}", headers=auth_headers
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_costs_by_tag_and_scorecard_executive(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    by_tag = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs/by-tag?tag_key=environment",
        headers=auth_headers,
    )
    assert by_tag.status_code == 200

    exec_sc = await client.get(
        f"/v1/orgs/{owner['org_id']}/scorecard/executive", headers=auth_headers
    )
    assert exec_sc.status_code == 200

    hist = await client.get(
        f"/v1/orgs/{owner['org_id']}/forecasts/history", headers=auth_headers
    )
    assert hist.status_code == 200


@pytest.mark.asyncio
async def test_api_key_auth_and_revoke(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    created = await client.post(
        f"/v1/orgs/{owner['org_id']}/api-keys/",
        headers=auth_headers,
        json={"name": "Automation", "scopes": ["cost.read"]},
    )
    assert created.status_code == 201, created.text
    raw = created.json().get("raw_key") or created.json().get("key")
    key_id = created.json()["id"]
    assert raw

    # API key can read costs
    costs = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert costs.status_code == 200, costs.text

    revoked = await client.delete(
        f"/v1/orgs/{owner['org_id']}/api-keys/{key_id}", headers=auth_headers
    )
    assert revoked.status_code == 200

    after = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_team_role_change_and_remove(
    client: AsyncClient, auth_headers: dict, owner: dict, clean_db
) -> None:
    member = await _create_verified_user(
        clean_db,
        email="teameditor@example.com",
        org_name="Temp Org",
        role="owner",
        name="Temp",
    )
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM team_members WHERE user_id = $1", member["user_id"])
        row = await conn.fetchrow(
            """
            INSERT INTO team_members (org_id, user_id, role, invite_accepted)
            VALUES ($1, $2, 'editor', TRUE)
            RETURNING id
            """,
            owner["org_id"],
            member["user_id"],
        )

    role = await client.put(
        f"/v1/orgs/{owner['org_id']}/team/{row['id']}/role",
        headers=auth_headers,
        json={"role": "viewer"},
    )
    assert role.status_code == 200, role.text

    removed = await client.delete(
        f"/v1/orgs/{owner['org_id']}/team/{row['id']}", headers=auth_headers
    )
    assert removed.status_code == 200
