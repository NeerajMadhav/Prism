"""Concurrent / multi-request load checks against realtime DB + Redis."""

from __future__ import annotations

import asyncio
from collections import Counter

import pytest
from httpx import AsyncClient

from tests.conftest import STRONG_PASSWORD


@pytest.mark.asyncio
async def test_concurrent_authenticated_cost_reads(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    """50 parallel GETs must all succeed without pool / cache errors."""
    path = f"/v1/orgs/{owner['org_id']}/costs"

    async def one() -> int:
        res = await client.get(path, headers=auth_headers)
        return res.status_code

    codes = await asyncio.gather(*[one() for _ in range(50)])
    assert Counter(codes)[200] == 50, f"statuses={Counter(codes)}"


@pytest.mark.asyncio
async def test_concurrent_mixed_dashboard_reads(
    client: AsyncClient, auth_headers: dict, owner: dict, seeded_costs: dict
) -> None:
    """Burst of mixed dashboard endpoints under one org."""
    oid = owner["org_id"]
    paths = [
        f"/v1/orgs/{oid}/costs",
        f"/v1/orgs/{oid}/costs/by-service",
        f"/v1/orgs/{oid}/costs/by-day",
        f"/v1/orgs/{oid}/alerts/",
        f"/v1/orgs/{oid}/caps/",
        f"/v1/orgs/{oid}/scorecard/",
        f"/v1/orgs/{oid}/forecasts/",
        f"/v1/orgs/{oid}/team",
        f"/v1/auth/me",
    ]

    async def one(path: str) -> tuple[str, int]:
        res = await client.get(path, headers=auth_headers)
        return path, res.status_code

    tasks = [one(paths[i % len(paths)]) for i in range(45)]
    results = await asyncio.gather(*tasks)
    failures = [(p, c) for p, c in results if c != 200]
    assert not failures, f"failures={failures[:10]}"


@pytest.mark.asyncio
async def test_concurrent_refresh_only_one_succeeds(
    client: AsyncClient, owner: dict
) -> None:
    """Same refresh token used in parallel → exactly one 200, rest 401."""
    login = await client.post(
        "/v1/auth/login",
        json={"email": owner["email"], "password": owner["password"]},
    )
    assert login.status_code == 200, login.text
    refresh = login.json()["refresh_token"]

    async def one() -> int:
        res = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
        return res.status_code

    codes = await asyncio.gather(*[one() for _ in range(20)])
    counts = Counter(codes)
    assert counts[200] == 1, f"expected single winner, got {counts}"
    assert counts[401] == 19, f"expected losers 401, got {counts}"


@pytest.mark.asyncio
async def test_concurrent_signups_unique_emails(client: AsyncClient) -> None:
    """Parallel signups with distinct emails all succeed."""

    async def one(i: int) -> int:
        res = await client.post(
            "/v1/auth/signup",
            json={
                "email": f"load{i}@example.com",
                "name": f"Load {i}",
                "password": STRONG_PASSWORD,
                "org_name": f"Load Org {i}",
            },
        )
        return res.status_code

    codes = await asyncio.gather(*[one(i) for i in range(15)])
    assert Counter(codes)[200] == 15, f"statuses={Counter(codes)}"


@pytest.mark.asyncio
async def test_concurrent_duplicate_signup_safe(client: AsyncClient) -> None:
    """Parallel identical signups → one 200, rest 409 (no 500)."""
    payload = {
        "email": "race@example.com",
        "name": "Race User",
        "password": STRONG_PASSWORD,
        "org_name": "Race Org",
    }

    async def one() -> int:
        res = await client.post("/v1/auth/signup", json=payload)
        return res.status_code

    codes = await asyncio.gather(*[one() for _ in range(10)])
    counts = Counter(codes)
    assert counts[200] == 1, f"got {counts}"
    assert counts[409] == 9, f"got {counts}"
    assert 500 not in counts


@pytest.mark.asyncio
async def test_health_under_parallel_ping(client: AsyncClient) -> None:
    codes = await asyncio.gather(*[client.get("/health") for _ in range(30)])
    assert all(r.status_code == 200 for r in codes)
    assert all(r.json()["db"] is True for r in codes)
    assert all(r.json()["status"] in ("ok", "degraded") for r in codes)
