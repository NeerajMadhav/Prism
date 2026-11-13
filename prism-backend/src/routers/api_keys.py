"""Org API key management and auth dependency."""

from datetime import UTC, datetime
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Header, Path
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.security import generate_token, hash_password, verify_password

router = APIRouter(prefix="/v1/orgs/{org_id}/api-keys", tags=["api-keys"])

VALID_SCOPES = {"cost.read", "alerts.read", "reports.read", "webhooks.write"}


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None


async def get_api_key_context(
    org_id: UUID = Path(..., alias="org_id"),
    authorization: str | None = Header(default=None),
    db: asyncpg.Connection = Depends(get_db),
) -> UserContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("Authentication required", status_code=401, code="unauthorized")
    token = authorization.split(" ", 1)[1]
    if not token.startswith("prism_"):
        raise AppError("Not an API key token", status_code=401, code="unauthorized")
    prefix = token[6:14]
    rows = await db.fetch(
        """
        SELECT * FROM api_keys
        WHERE org_id = $1 AND key_prefix = $2 AND revoked_at IS NULL
        """,
        org_id,
        prefix,
    )
    for row in rows:
        if verify_password(token, row["key_hash"]):
            if row["expires_at"] and row["expires_at"] < datetime.now(tz=UTC):
                raise AppError("API key expired", status_code=401, code="unauthorized")
            await db.execute("UPDATE api_keys SET last_used = NOW() WHERE id = $1", row["id"])
            return UserContext(
                user_id=row["user_id"],
                org_id=org_id,
                role="viewer",
                email="api-key@prism.local",
                scopes=list(row["scopes"] or []),
                is_api_key=True,
            )
    raise AppError("Invalid API key", status_code=401, code="unauthorized")


@router.get("/")
async def list_api_keys(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT id, name, key_prefix, scopes, expires_at, last_used, created_at, revoked_at
        FROM api_keys WHERE org_id = $1
        ORDER BY created_at DESC
        """,
        org["id"],
    )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "key_prefix": r["key_prefix"],
            "scopes": r["scopes"],
            "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            "last_used": r["last_used"].isoformat() if r["last_used"] else None,
            "created_at": r["created_at"].isoformat(),
            "revoked_at": r["revoked_at"].isoformat() if r["revoked_at"] else None,
        }
        for r in rows
    ]


@router.post("/", status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    org: dict = Depends(get_org_access),
    current_user: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    invalid = set(body.scopes) - VALID_SCOPES
    if invalid:
        raise AppError(f"Invalid scopes: {', '.join(sorted(invalid))}", status_code=400)
    raw = f"prism_{generate_token(24)}"
    row = await db.fetchrow(
        """
        INSERT INTO api_keys (org_id, user_id, key_hash, key_prefix, name, scopes, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, name, key_prefix, scopes, expires_at, created_at
        """,
        org["id"],
        current_user.user_id,
        hash_password(raw),
        raw[6:14],
        body.name,
        body.scopes,
        body.expires_at,
    )
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "key_prefix": row["key_prefix"],
        "scopes": row["scopes"],
        "raw_key": raw,
    }


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute(
        "UPDATE api_keys SET revoked_at = NOW() WHERE id = $1 AND org_id = $2",
        key_id,
        org["id"],
    )
    return {"message": "API key revoked"}
