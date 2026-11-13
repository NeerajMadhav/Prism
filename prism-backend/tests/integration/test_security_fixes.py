"""Regression tests for security root-cause fixes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.config.database import get_pool
from src.utils.security import create_access_token
from tests.conftest import STRONG_PASSWORD, _create_verified_user


@pytest.mark.asyncio
async def test_demoted_user_loses_admin_access_immediately(
    client: AsyncClient, auth_headers: dict, owner: dict, clean_db
) -> None:
    admin = await _create_verified_user(
        clean_db, email="demote@example.com", org_name="Tmp", role="owner"
    )
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM team_members WHERE user_id = $1", admin["user_id"])
        row = await conn.fetchrow(
            """
            INSERT INTO team_members (org_id, user_id, role, invite_accepted)
            VALUES ($1, $2, 'admin', TRUE) RETURNING id
            """,
            owner["org_id"],
            admin["user_id"],
        )

    # Token still says admin in JWT payload, but DB role is re-checked.
    token = create_access_token(
        admin["user_id"], owner["org_id"], "admin", admin["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Demote via owner
    demote = await client.put(
        f"/v1/orgs/{owner['org_id']}/team/{row['id']}/role",
        headers=auth_headers,
        json={"role": "viewer"},
    )
    assert demote.status_code == 200, demote.text

    # Same JWT must no longer pass admin-only LLM update
    blocked = await client.put(
        f"/v1/orgs/{owner['org_id']}/llm/",
        headers=headers,
        json={"is_enabled": True},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_removed_member_jwt_rejected(
    client: AsyncClient, auth_headers: dict, owner: dict, clean_db
) -> None:
    member = await _create_verified_user(
        clean_db, email="kick@example.com", org_name="Tmp2", role="owner"
    )
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM team_members WHERE user_id = $1", member["user_id"])
        row = await conn.fetchrow(
            """
            INSERT INTO team_members (org_id, user_id, role, invite_accepted)
            VALUES ($1, $2, 'editor', TRUE) RETURNING id
            """,
            owner["org_id"],
            member["user_id"],
        )

    token = create_access_token(
        member["user_id"], owner["org_id"], "editor", member["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=headers)
    ).status_code == 200

    removed = await client.delete(
        f"/v1/orgs/{owner['org_id']}/team/{row['id']}", headers=auth_headers
    )
    assert removed.status_code == 200

    after = await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=headers)
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_api_key_scope_enforced(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    created = await client.post(
        f"/v1/orgs/{owner['org_id']}/api-keys/",
        headers=auth_headers,
        json={"name": "Costs only", "scopes": ["cost.read"]},
    )
    assert created.status_code == 201, created.text
    raw = created.json()["raw_key"]
    key_headers = {"Authorization": f"Bearer {raw}"}

    costs = await client.get(f"/v1/orgs/{owner['org_id']}/costs", headers=key_headers)
    assert costs.status_code == 200

    # No alerts.read scope → forbidden
    alerts = await client.get(f"/v1/orgs/{owner['org_id']}/alerts/", headers=key_headers)
    assert alerts.status_code == 403

    # Unscoped path for API keys (team) → forbidden
    team = await client.get(f"/v1/orgs/{owner['org_id']}/team", headers=key_headers)
    assert team.status_code == 403


@pytest.mark.asyncio
async def test_change_password_revokes_refresh(
    client: AsyncClient, owner: dict
) -> None:
    login = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": owner["password"]},
    )
    assert login.status_code == 200
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    changed = await client.post(
        "/v1/auth/change-password",
        headers=headers,
        json={"current_password": STRONG_PASSWORD, "new_password": "NewSecret1!"},
    )
    assert changed.status_code == 200, changed.text

    reuse = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401

    # restore password for other tests that reuse owner fixture in same DB... 
    # clean_db truncates between tests, so OK.
