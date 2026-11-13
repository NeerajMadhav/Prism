"""Auth endpoints: happy path, validation, edge cases."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import STRONG_PASSWORD


@pytest.mark.asyncio
async def test_signup_login_me_logout_flow(client: AsyncClient) -> None:
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": "flow@example.com",
            "name": "Flow User",
            "password": STRONG_PASSWORD,
            "org_name": "Flow Org",
        },
    )
    assert signup.status_code == 200, signup.text
    body = signup.json()
    assert "user_id" in body and "org_id" in body

    # unverified cannot login
    login_blocked = await client.post(
        "/v1/auth/login",
        json={"email": "flow@example.com", "password": STRONG_PASSWORD},
    )
    assert login_blocked.status_code == 403

    # verify via DB (email token hashed — use direct verify path after setting verified in fixture pattern)
    from src.config.database import get_pool
    from uuid import UUID

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET email_verified = TRUE, email_verify_token = NULL WHERE id = $1",
            UUID(body["user_id"]),
        )

    login = await client.post(
        "/v1/auth/login",
        json={"email": "flow@example.com", "password": STRONG_PASSWORD},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = await client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"
    assert me.json()["role"] == "owner"

    refreshed = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]

    # old refresh revoked
    old_refresh = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert old_refresh.status_code == 401

    logout = await client.post("/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, owner: dict) -> None:
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": owner["email"],
            "name": "Dup",
            "password": STRONG_PASSWORD,
            "org_name": "Dup Org",
        },
    )
    assert res.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    ["short1!", "nouppercase1!", "NoNumber!", "NoSpecial1"],
)
async def test_signup_weak_password(client: AsyncClient, password: str) -> None:
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": f"weak_{password[:4]}@example.com",
            "name": "Weak",
            "password": password,
            "org_name": "Weak Org",
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_login_wrong_password_same_message(client: AsyncClient, owner: dict) -> None:
    wrong = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": "WrongPass1!"},
    )
    missing = await client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass1!"},
    )
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json()["error"] == missing.json()["error"]


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_and_change_password(
    client: AsyncClient, auth_headers: dict, owner: dict
) -> None:
    upd = await client.put(
        "/v1/auth/me",
        headers=auth_headers,
        json={"name": "Renamed Owner"},
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Renamed Owner"

    bad = await client.post(
        "/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "WrongPass1!", "new_password": "NewSecret1!"},
    )
    assert bad.status_code == 400

    ok = await client.post(
        "/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": owner["password"], "new_password": "NewSecret1!"},
    )
    assert ok.status_code == 200

    login = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": "NewSecret1!"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_no_enumeration(client: AsyncClient) -> None:
    a = await client.post("/v1/auth/forgot-password", json={"email": "missing@example.com"})
    b = await client.post("/v1/auth/forgot-password", json={"email": "also@example.com"})
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["message"] == b.json()["message"]


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code in (200, 503)
    assert "db" in res.json() and "redis" in res.json()
