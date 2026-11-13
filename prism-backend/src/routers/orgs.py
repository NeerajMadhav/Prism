"""Organization settings routes."""

import asyncpg
from fastapi import APIRouter, Depends

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.schemas.orgs import OrgUpdateRequest
from src.types.models import UserContext

router = APIRouter(prefix="/v1/orgs", tags=["orgs"])


def _serialize_org(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "plan": row["plan"],
        "billing_period_start": row["billing_period_start"].isoformat()
        if row["billing_period_start"]
        else None,
        "currency": row["currency"],
        "timezone": row["timezone"],
        "feature_flags": row["feature_flags"] or {},
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/{org_id}")
async def get_org(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
) -> dict:
    return _serialize_org(org)  # type: ignore[arg-type]


@router.put("/{org_id}")
async def update_org(
    body: OrgUpdateRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    org_id = org["id"]
    row = await db.fetchrow(
        """
        UPDATE organizations
        SET name = COALESCE($1, name),
            timezone = COALESCE($2, timezone),
            currency = COALESCE($3, currency),
            billing_period_start = COALESCE($4, billing_period_start)
        WHERE id = $5
        RETURNING *
        """,
        body.name,
        body.timezone,
        body.currency,
        body.billing_period_start,
        org_id,
    )
    if not row:
        from src.utils.errors import AppError

        raise AppError("Organization not found", status_code=403)
    return _serialize_org(row)
