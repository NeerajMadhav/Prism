"""Shared fixtures: test DB, Redis, authenticated clients, mock cloud data."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient

# Test env — must be set before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://prism:prism@127.0.0.1:55432/prism_test"
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6380/0")
os.environ["CELERY_BROKER_URL"] = os.environ.get(
    "TEST_CELERY_BROKER_URL", "redis://127.0.0.1:6380/1"
)
os.environ["CELERY_RESULT_BACKEND"] = os.environ.get(
    "TEST_CELERY_RESULT_BACKEND", "redis://127.0.0.1:6380/2"
)
os.environ["JWT_ACCESS_SECRET"] = "test-access-secret-min-32-chars!!"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret-min-32-chars!"
os.environ["ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["AWS_SES_FROM"] = "noreply@example.com"
os.environ["PRISM_AWS_ACCOUNT_ID"] = "123456789012"

from src.config.database import close_db, init_db  # noqa: E402
from src.config.redis_client import close_redis, init_redis  # noqa: E402
from src.config.settings import get_settings  # noqa: E402
from src.main import create_app  # noqa: E402
from src.middleware.rate_limit import limiter  # noqa: E402
from src.utils.encrypt import aes_encrypt  # noqa: E402
from src.utils.security import create_access_token, hash_password  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "src" / "db" / "schema.sql"

STRONG_PASSWORD = "Secret1!"


def _split_sql(sql: str) -> list[str]:
    """Split schema SQL into executable statements (skip empty / comments-only)."""
    stmts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            buf = []
            if stmt:
                stmts.append(stmt)
    if buf:
        stmt = "\n".join(buf).strip()
        if stmt:
            stmts.append(stmt)
    return stmts


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    get_settings.cache_clear()
    dsn = os.environ["DATABASE_URL"]
    # Wait for DB
    last_err: Exception | None = None
    for _ in range(40):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.execute("SELECT 1")
            await conn.close()
            last_err = None
            break
        except Exception as exc:
            last_err = exc
            import asyncio

            await asyncio.sleep(0.5)
    if last_err is not None:
        pytest.skip(f"PostgreSQL test container not available: {last_err}")

    admin = await asyncpg.connect(dsn)
    # Reset schema for clean suite, then reinstall extensions
    await admin.execute(
        """
        DROP SCHEMA IF EXISTS public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO prism;
        GRANT ALL ON SCHEMA public TO public;
        """
    )
    await admin.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    await admin.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    # Split statements — asyncpg execute() can struggle with multi-statement + SELECT create_hypertable
    for stmt in _split_sql(schema_sql):
        await admin.execute(stmt)
    await admin.close()

    pool = await init_db()
    yield pool
    await close_db()


@pytest_asyncio.fixture(scope="session")
async def redis_client() -> AsyncIterator[Any]:
    get_settings.cache_clear()
    for _ in range(40):
        try:
            r = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
            assert await r.ping()
            await r.aclose()
            break
        except Exception:
            import asyncio

            await asyncio.sleep(0.5)
    else:
        pytest.skip("Redis test container not available")

    client = await init_redis()
    yield client
    await close_redis()


@pytest_asyncio.fixture
async def clean_db(db_pool: asyncpg.Pool, redis_client: Any) -> AsyncIterator[asyncpg.Pool]:
    """Truncate all tables between tests for isolation."""
    async with db_pool.acquire() as conn:
        tables = await conn.fetch(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename NOT LIKE '%hypertable%'
            """
        )
        names = [t["tablename"] for t in tables if t["tablename"] != "cost_records"]
        if names:
            await conn.execute("TRUNCATE " + ", ".join(f'"{n}"' for n in names) + " CASCADE")
        # cost_records may be hypertable — delete
        try:
            await conn.execute("DELETE FROM cost_records")
        except Exception:
            pass
    await redis_client.flushdb()
    yield db_pool


@pytest_asyncio.fixture
async def app(clean_db: asyncpg.Pool, redis_client: Any):
    get_settings.cache_clear()
    # In-memory slowapi counters persist across tests; disable unless a test re-enables.
    limiter.enabled = False
    return create_app()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    # Follow trailing-slash 307s so /alerts and /alerts/ both work in tests.
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac


@pytest.fixture
def enable_rate_limit() -> Iterator[None]:
    """Turn rate limiting on for the dedicated rate-limit test only."""
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = False


async def _create_verified_user(
    db: asyncpg.Pool,
    *,
    email: str,
    name: str = "Test User",
    org_name: str = "Test Org",
    role: str = "owner",
    password: str = STRONG_PASSWORD,
) -> dict[str, Any]:
    async with db.acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow(
                """
                INSERT INTO users (email, name, password_hash, email_verified)
                VALUES ($1, $2, $3, TRUE)
                RETURNING id, email, name
                """,
                email.lower(),
                name,
                hash_password(password),
            )
            org = await conn.fetchrow(
                "INSERT INTO organizations (name) VALUES ($1) RETURNING id, name",
                org_name,
            )
            await conn.execute(
                """
                INSERT INTO team_members (org_id, user_id, role, invite_accepted)
                VALUES ($1, $2, $3, TRUE)
                """,
                org["id"],
                user["id"],
                role,
            )
            await conn.execute(
                "INSERT INTO notification_settings (org_id, alert_emails) VALUES ($1, $2)",
                org["id"],
                [email.lower()],
            )
    return {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "org_id": org["id"],
        "org_name": org["name"],
        "role": role,
        "password": password,
    }


@pytest_asyncio.fixture
async def owner(clean_db: asyncpg.Pool) -> dict[str, Any]:
    return await _create_verified_user(clean_db, email="owner@example.com", org_name="Acme Corp")


@pytest_asyncio.fixture
async def other_org_owner(clean_db: asyncpg.Pool) -> dict[str, Any]:
    return await _create_verified_user(
        clean_db, email="other@example.com", org_name="Other Corp", name="Other Owner"
    )


@pytest_asyncio.fixture
async def auth_headers(owner: dict[str, Any]) -> dict[str, str]:
    token = create_access_token(
        owner["user_id"], owner["org_id"], owner["role"], owner["email"]
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_auth_headers(other_org_owner: dict[str, Any]) -> dict[str, str]:
    token = create_access_token(
        other_org_owner["user_id"],
        other_org_owner["org_id"],
        other_org_owner["role"],
        other_org_owner["email"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded_costs(clean_db: asyncpg.Pool, owner: dict[str, Any]) -> dict[str, Any]:
    """Insert mock AWS cloud account + cost_records for dashboard tests."""
    async with clean_db.acquire() as conn:
        group = await conn.fetchrow(
            """
            INSERT INTO account_groups (org_id, provider, name, scope)
            VALUES ($1, 'aws', 'AWS Accounts', 'account')
            RETURNING id
            """,
            owner["org_id"],
        )
        creds = aes_encrypt('{"role_arn":"arn:aws:iam::111122223333:role/Prism","external_id":"ext","region":"us-east-1"}')
        account = await conn.fetchrow(
            """
            INSERT INTO cloud_accounts
              (org_id, group_id, provider, account_id, display_name, scope, credentials_enc,
               last_sync_status, data_as_of, is_active)
            VALUES ($1, $2, 'aws', '111122223333', 'Prod AWS', 'account', $3, 'success', CURRENT_DATE, TRUE)
            RETURNING id
            """,
            owner["org_id"],
            group["id"],
            creds,
        )
        today = date.today()
        month_start = date(today.year, today.month, 1)
        rows = []
        for i in range(1, min(today.day, 10) + 1):
            d = month_start + timedelta(days=i - 1)
            if d > today:
                break
            ts = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            rows.append(
                (
                    owner["org_id"],
                    account["id"],
                    "aws",
                    ts,
                    "Amazon EC2",
                    "us-east-1",
                    100.0 + i,
                    100.0 + i,
                    95.0 + i,
                    False,
                )
            )
            rows.append(
                (
                    owner["org_id"],
                    account["id"],
                    "aws",
                    ts,
                    "Amazon S3",
                    "us-east-1",
                    20.0 + i,
                    20.0 + i,
                    20.0 + i,
                    False,
                )
            )
        await conn.executemany(
            """
            INSERT INTO cost_records
              (org_id, account_id, provider, time, service, region,
               cost_usd, cost_unblended_usd, cost_amortized_usd, is_estimate)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
            rows,
        )
    return {"account_id": account["id"], "org_id": owner["org_id"]}


# Mock cloud connector responses
MOCK_COST_ROWS = [
    {
        "time": datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(days=1),
        "service": "Amazon EC2",
        "region": "us-east-1",
        "cost_usd": 42.5,
        "cost_unblended_usd": 42.5,
        "cost_amortized_usd": 40.0,
        "usage_quantity": 24.0,
        "usage_unit": "Hrs",
        "tags": {"environment": "prod"},
        "is_estimate": True,
    }
]
