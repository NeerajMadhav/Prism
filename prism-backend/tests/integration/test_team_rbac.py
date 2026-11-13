"""Team invite + RBAC + multi-tenant isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.config.database import get_pool
from src.utils.security import hash_password
from tests.conftest import STRONG_PASSWORD, _create_verified_user


@pytest.mark.asyncio
async def test_invite_accept_viewer_cannot_create_cap(
    client: AsyncClient, auth_headers: dict, owner: dict, clean_db
) -> None:
    invite = await client.post(
        f"/v1/orgs/{owner['org_id']}/team/invite",
        headers=auth_headers,
        json={"email": "viewer@example.com", "role": "viewer"},
    )
    assert invite.status_code in (200, 201), invite.text

    # Pull raw token from DB by replacing hash with known token for accept
    raw = "a" * 64
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE invites SET token_hash = $1, expires_at = $2
            WHERE org_id = $3 AND email = $4 AND accepted_at IS NULL
            """,
            hash_password(raw),
            datetime.now(tz=timezone.utc) + timedelta(hours=24),
            owner["org_id"],
            "viewer@example.com",
        )

    accept = await client.post(
        f"/v1/orgs/{owner['org_id']}/team/accept-invite",
        json={
            "token": raw,
            "org_id": str(owner["org_id"]),
            "name": "Viewer Person",
            "password": STRONG_PASSWORD,
        },
    )
    # accept-invite path may be /team/accept-invite without org in some impls
    if accept.status_code == 404:
        accept = await client.post(
            "/v1/orgs/{}/team/accept-invite".format(owner["org_id"]),
            json={
                "token": raw,
                "org_id": str(owner["org_id"]),
                "name": "Viewer Person",
                "password": STRONG_PASSWORD,
            },
        )
    assert accept.status_code in (200, 201), accept.text

    login = await client.post(
        "/v1/auth/login",
        json={"email": "viewer@example.com", "password": STRONG_PASSWORD},
    )
    assert login.status_code == 200, login.text
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # viewer can read costs (may be empty)
    costs = await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=viewer_headers)
    assert costs.status_code == 200

    # viewer cannot create cap
    cap = await client.post(
        f"/v1/orgs/{owner['org_id']}/caps",
        headers=viewer_headers,
        json={
            "name": "AWS Cap",
            "scope": "platform",
            "scope_value": "aws",
            "cap_amount": 1000,
            "period": "monthly",
        },
    )
    assert cap.status_code == 403


@pytest.mark.asyncio
async def test_cross_org_access_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    owner: dict,
    other_org_owner: dict,
    other_auth_headers: dict,
) -> None:
    # Owner A cannot read Org B
    res = await client.get(
        f"/v1/orgs/{other_org_owner['org_id']}",
        headers=auth_headers,
    )
    assert res.status_code == 403

    # Owner B cannot read Org A costs
    res2 = await client.get(
        f"/v1/orgs/{owner['org_id']}/costs",
        headers=other_auth_headers,
    )
    assert res2.status_code == 403


@pytest.mark.asyncio
async def test_cannot_invite_owner_role(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    res = await client.post(
        f"/v1/orgs/{owner['org_id']}/team/invite",
        headers=auth_headers,
        json={"email": "newowner@example.com", "role": "owner"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_list_team_members(client: AsyncClient, auth_headers: dict, owner: dict) -> None:
    res = await client.get(f"/v1/orgs/{owner['org_id']}/team", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    members = data if isinstance(data, list) else data.get("data", data)
    assert any(m.get("role") == "owner" or m.get("email") == owner["email"] for m in members)
