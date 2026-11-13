"""Full end-to-end journey with mock cloud data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.config.database import get_pool
from src.utils.security import hash_password
from tests.conftest import STRONG_PASSWORD


@pytest.mark.asyncio
async def test_full_user_journey_e2e(client: AsyncClient) -> None:
    """
    Signup → verify → login → /me → invite editor → accept →
    connect AWS (mocked celery) → seed costs → create cap →
    read dashboard → set report → list alerts.
    """
    # 1. Signup
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": "e2e@example.com",
            "name": "E2E Owner",
            "password": STRONG_PASSWORD,
            "org_name": "E2E Corp",
        },
    )
    assert signup.status_code == 200, signup.text
    user_id = signup.json()["user_id"]
    org_id = signup.json()["org_id"]

    # 2. Verify email (simulate click)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET email_verified = TRUE, email_verify_token = NULL WHERE id = $1",
            UUID(user_id),
        )

    # 3. Login + me
    login = await client.post(
        "/v1/auth/login",
        json={"email": "e2e@example.com", "password": STRONG_PASSWORD},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = await client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["org_id"] == org_id
    assert me.json()["role"] == "owner"

    # 4. Invite editor
    invite = await client.post(
        f"/v1/orgs/{org_id}/team/invite",
        headers=headers,
        json={"email": "editor@example.com", "role": "editor"},
    )
    assert invite.status_code == 201, invite.text

    raw = "b" * 64
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE invites SET token_hash = $1, expires_at = $2
            WHERE org_id = $3 AND email = 'editor@example.com' AND accepted_at IS NULL
            """,
            hash_password(raw),
            datetime.now(tz=timezone.utc) + timedelta(days=1),
            UUID(org_id),
        )

    accept = await client.post(
        f"/v1/orgs/{org_id}/team/accept-invite",
        json={
            "token": raw,
            "org_id": org_id,
            "name": "E2E Editor",
            "password": STRONG_PASSWORD,
        },
    )
    assert accept.status_code == 200, accept.text

    editor_login = await client.post(
        "/v1/auth/login",
        json={"email": "editor@example.com", "password": STRONG_PASSWORD},
    )
    assert editor_login.status_code == 200
    editor_headers = {"Authorization": f"Bearer {editor_login.json()['access_token']}"}

    # 5. Connect AWS (admin) — mock sync scheduler
    with patch(
        "src.routers.accounts.schedule_sync_or_inline",
        return_value=("task-e2e", "queued"),
    ):
        acct = await client.post(
            f"/v1/orgs/{org_id}/accounts",
            headers=headers,
            json={
                "provider": "aws",
                "display_name": "E2E AWS",
                "scope": "account",
                "credentials": {
                    "role_arn": "arn:aws:iam::444455556666:role/Prism",
                    "external_id": "e2e-ext",
                    "region": "us-east-1",
                },
            },
        )
    assert acct.status_code == 201, acct.text
    account_id = acct.json()["id"]

    # 6. Seed realtime mock cost data
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO cost_records
              (org_id, account_id, provider, time, service, region,
               cost_usd, cost_unblended_usd, cost_amortized_usd, tags, is_estimate)
            VALUES
              ($1, $2, 'aws', date_trunc('day', NOW()) - interval '1 day',
               'Amazon EC2', 'us-east-1', 250.5, 250.5, 240.0,
               '{"environment":"prod"}'::jsonb, TRUE),
              ($1, $2, 'aws', date_trunc('day', NOW()) - interval '2 day',
               'Amazon S3', 'us-east-1', 40.0, 40.0, 40.0,
               '{"environment":"prod"}'::jsonb, FALSE)
            """,
            UUID(org_id),
            UUID(account_id),
        )

    # 7. Dashboard
    costs = await client.get(f"/v1/orgs/{org_id}/costs", headers=editor_headers)
    assert costs.status_code == 200, costs.text

    # 8. Editor creates cap — mock alerts celery
    with patch("src.routers.caps.check_org_alerts") as mock_alerts:
        mock_alerts.delay = MagicMock()
        cap = await client.post(
            f"/v1/orgs/{org_id}/caps/",
            headers=editor_headers,
            json={
                "name": "E2E AWS Cap",
                "scope": "platform",
                "scope_value": "aws",
                "cap_amount": 100,
                "period": "monthly",
            },
        )
    assert cap.status_code == 201, cap.text

    # 9. Configure report
    report = await client.put(
        f"/v1/orgs/{org_id}/reports",
        headers=headers,
        json={
            "is_active": True,
            "recipient_emails": ["e2e@example.com"],
            "send_day": 1,
            "include_recommendations": True,
        },
    )
    assert report.status_code == 200, report.text

    # 10. Notifications update
    notif = await client.put(
        f"/v1/orgs/{org_id}/notifications",
        headers=headers,
        json={"alert_emails": ["e2e@example.com", "editor@example.com"]},
    )
    assert notif.status_code == 200, notif.text

    # 11. Shared org: both see same team
    team = await client.get(f"/v1/orgs/{org_id}/team", headers=editor_headers)
    assert team.status_code == 200
    members = team.json()
    emails = {m["email"] for m in members}
    assert "e2e@example.com" in emails
    assert "editor@example.com" in emails
