"""Cloud account CRUD and sync triggers."""

import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.config.database import get_db
from src.config.redis_client import redis_incr
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.schemas.accounts import (
    AccountCreateRequest,
    AccountUpdateRequest,
    HealthCheckResponse,
    SyncTriggerResponse,
)
from src.schemas.auth import MessageResponse
from src.services.connectors import extract_aws_account_id, get_connector
from src.services.fx_service import get_usd_rate
from src.types.models import UserContext
from src.utils.encrypt import aes_decrypt, aes_encrypt
from src.utils.errors import AppError
from src.utils.logger import get_logger
from src.utils.pagination import get_pagination, paginated_response
from src.workers.sync_worker import schedule_sync_or_inline

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/orgs/{org_id}/accounts", tags=["accounts"])


def _serialize_account(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "provider": row["provider"],
        "account_id": row["account_id"],
        "display_name": row["display_name"],
        "scope": row["scope"],
        "last_sync": row["last_sync"].isoformat() if row["last_sync"] else None,
        "last_sync_status": row["last_sync_status"],
        "last_sync_error": row["last_sync_error"],
        "data_as_of": row["data_as_of"].isoformat() if row["data_as_of"] else None,
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat(),
    }


def _provider_account_id(provider: str, credentials: dict) -> str:
    try:
        if provider == "aws":
            return extract_aws_account_id(credentials["role_arn"])
        if provider == "azure":
            return str(credentials["subscription_id"])
        if provider == "gcp":
            return str(credentials["project_id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError(str(exc) or "Invalid cloud credentials", status_code=400) from exc
    raise AppError("Unsupported provider", status_code=400)


async def _ensure_account_group(
    db: asyncpg.Connection, org_id: UUID, provider: str, scope: str
) -> UUID:
    existing = await db.fetchrow(
        """
        SELECT id FROM account_groups
        WHERE org_id = $1 AND provider = $2 AND scope = $3
        LIMIT 1
        """,
        org_id,
        provider,
        scope,
    )
    if existing:
        return existing["id"]
    created = await db.fetchrow(
        """
        INSERT INTO account_groups (org_id, provider, name, scope)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        org_id,
        provider,
        f"{provider}-{scope}",
        scope,
    )
    return created["id"]


@router.get("")
async def list_accounts(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT * FROM cloud_accounts
        WHERE org_id = $1 AND is_active = TRUE
        ORDER BY created_at DESC
        """,
        org["id"],
    )
    return [_serialize_account(r) for r in rows]


@router.post("", status_code=201)
async def create_account(
    body: AccountCreateRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    cloud_account_id = _provider_account_id(body.provider, body.credentials)
    dup = await db.fetchval(
        """
        SELECT 1 FROM cloud_accounts
        WHERE org_id = $1 AND provider = $2 AND account_id = $3
        """,
        org["id"],
        body.provider,
        cloud_account_id,
    )
    if dup:
        raise AppError(
            "This cloud account ID is already connected. "
            "You can add another account of the same provider with a different account ID.",
            status_code=409,
            code="conflict",
        )

    group_id = await _ensure_account_group(db, org["id"], body.provider, body.scope)
    enc = aes_encrypt(json.dumps(body.credentials))

    async with db.transaction():
        row = await db.fetchrow(
            """
            INSERT INTO cloud_accounts (
              org_id, group_id, provider, account_id, display_name, scope, credentials_enc
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            org["id"],
            group_id,
            body.provider,
            cloud_account_id,
            body.display_name,
            body.scope,
            enc,
        )
        exists_settings = await db.fetchval(
            "SELECT 1 FROM notification_settings WHERE org_id = $1",
            org["id"],
        )
        if not exists_settings:
            await db.execute(
                "INSERT INTO notification_settings (org_id) VALUES ($1)",
                org["id"],
            )

    task_id, sync_mode = schedule_sync_or_inline(
        account_id=row["id"],
        org_id=org["id"],
        backfill=True,
    )
    logger.info(
        "account_connected",
        account_id=str(row["id"]),
        org_id=str(org["id"]),
        provider=row["provider"],
        cloud_account_id=row["account_id"],
        sync_mode=sync_mode,
        sync_task_id=task_id,
    )
    return {
        "id": str(row["id"]),
        "provider": row["provider"],
        "account_id": row["account_id"],
        "display_name": row["display_name"],
        "last_sync_status": row["last_sync_status"],
        "created_at": row["created_at"].isoformat(),
        "sync_task_id": task_id,
        "sync_mode": sync_mode,
    }


@router.get("/{account_id}")
async def get_account(
    account_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        "SELECT * FROM cloud_accounts WHERE id = $1 AND org_id = $2",
        account_id,
        org["id"],
    )
    if not row:
        raise AppError("Account not found", status_code=404)
    return _serialize_account(row)


@router.put("/{account_id}")
async def update_account(
    account_id: UUID,
    body: AccountUpdateRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    existing = await db.fetchrow(
        "SELECT * FROM cloud_accounts WHERE id = $1 AND org_id = $2",
        account_id,
        org["id"],
    )
    if not existing:
        raise AppError("Account not found", status_code=404)

    credentials_enc = existing["credentials_enc"]
    last_sync_status = existing["last_sync_status"]
    if body.credentials is not None:
        credentials_enc = aes_encrypt(json.dumps(body.credentials))
        last_sync_status = "never"

    row = await db.fetchrow(
        """
        UPDATE cloud_accounts
        SET display_name = COALESCE($1, display_name),
            credentials_enc = $2,
            last_sync_status = $3
        WHERE id = $4 AND org_id = $5
        RETURNING *
        """,
        body.display_name,
        credentials_enc,
        last_sync_status,
        account_id,
        org["id"],
    )
    return _serialize_account(row)  # type: ignore[arg-type]


@router.delete("/{account_id}", response_model=MessageResponse)
async def delete_account(
    account_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> MessageResponse:
    updated = await db.execute(
        """
        UPDATE cloud_accounts SET is_active = FALSE
        WHERE id = $1 AND org_id = $2
        """,
        account_id,
        org["id"],
    )
    if updated == "UPDATE 0":
        raise AppError("Account not found", status_code=404)
    return MessageResponse(message="Account deactivated")


@router.post("/{account_id}/test", response_model=HealthCheckResponse)
async def test_account(
    account_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> HealthCheckResponse:
    row = await db.fetchrow(
        "SELECT * FROM cloud_accounts WHERE id = $1 AND org_id = $2 AND is_active = TRUE",
        account_id,
        org["id"],
    )
    if not row:
        raise AppError("Account not found", status_code=404)
    org_row = await db.fetchrow("SELECT currency FROM organizations WHERE id = $1", org["id"])
    fx_rate = await get_usd_rate(org_row["currency"] if org_row else "USD")
    connector = get_connector(
        row["provider"],
        aes_decrypt(row["credentials_enc"]),
        row["account_id"],
        fx_rate=fx_rate,
    )
    result = await connector.health_check()
    return HealthCheckResponse(ok=result.ok, error=result.error)


@router.post("/{account_id}/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    account_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> SyncTriggerResponse:
    row = await db.fetchrow(
        "SELECT id FROM cloud_accounts WHERE id = $1 AND org_id = $2 AND is_active = TRUE",
        account_id,
        org["id"],
    )
    if not row:
        raise AppError("Account not found", status_code=404)

    rl_key = f"rl:sync:{account_id}"
    count = await redis_incr(rl_key, expire_seconds=3600)
    if count is not None and count > 5:
        raise AppError("Sync rate limit exceeded for this account", status_code=429)

    task_id, sync_mode = schedule_sync_or_inline(
        account_id=account_id,
        org_id=org["id"],
        backfill=False,
    )
    message = "Sync queued" if sync_mode == "queued" else "Sync started inline (no Celery)"
    return SyncTriggerResponse(message=message, task_id=task_id)


@router.get("/{account_id}/sync-logs")
async def list_sync_logs(
    account_id: UUID,
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    exists = await db.fetchval(
        "SELECT 1 FROM cloud_accounts WHERE id = $1 AND org_id = $2",
        account_id,
        org["id"],
    )
    if not exists:
        raise AppError("Account not found", status_code=404)

    pg = get_pagination(request)
    total = await db.fetchval(
        "SELECT COUNT(*) FROM sync_logs WHERE account_id = $1 AND org_id = $2",
        account_id,
        org["id"],
    )
    rows = await db.fetch(
        """
        SELECT id, status, started_at, finished_at, records_synced, error
        FROM sync_logs
        WHERE account_id = $1 AND org_id = $2
        ORDER BY started_at DESC
        LIMIT $3 OFFSET $4
        """,
        account_id,
        org["id"],
        pg["limit"],
        pg["offset"],
    )
    data = [
        {
            "id": str(r["id"]),
            "status": r["status"],
            "started_at": r["started_at"].isoformat(),
            "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
            "records_synced": r["records_synced"],
            "error": r["error"],
        }
        for r in rows
    ]
    return paginated_response(data, int(total or 0), pg["page"], pg["limit"])
