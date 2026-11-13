"""Cloud resource inventory routes."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.pagination import get_pagination, paginated_response

router = APIRouter(prefix="/v1/orgs/{org_id}/resources", tags=["resources"])


@router.get("/")
async def list_resources(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    params = get_pagination(request)
    filters = ["org_id = $1"]
    args: list = [org["id"]]
    if request.query_params.get("provider"):
        args.append(request.query_params["provider"])
        filters.append(f"provider = ${len(args)}")
    if request.query_params.get("idle", "").lower() == "true":
        filters.append("is_idle = TRUE")
    where = " AND ".join(filters)
    total = await db.fetchval(f"SELECT COUNT(*) FROM resources WHERE {where}", *args)
    rows = await db.fetch(
        f"""
        SELECT * FROM resources WHERE {where}
        ORDER BY last_cost_usd DESC NULLS LAST
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        params["limit"],
        params["offset"],
    )
    return paginated_response([_serialize(r) for r in rows], int(total or 0), params["page"], params["limit"])


@router.get("/idle")
async def list_idle_resources(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT * FROM resources
        WHERE org_id = $1 AND is_idle = TRUE
        ORDER BY idle_since ASC NULLS LAST, last_cost_usd DESC NULLS LAST
        LIMIT 100
        """,
        org["id"],
    )
    return [_serialize(r) for r in rows]


@router.get("/{resource_id}")
async def get_resource(
    resource_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        "SELECT * FROM resources WHERE id = $1 AND org_id = $2",
        resource_id,
        org["id"],
    )
    if row is None:
        raise AppError("Resource not found", status_code=404)
    return _serialize(row)


def _serialize(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "provider": row["provider"],
        "resource_id": row["resource_id"],
        "resource_type": row["resource_type"],
        "name": row["name"],
        "region": row["region"],
        "tags": row["tags"],
        "last_cost_usd": float(row["last_cost_usd"] or 0) if row["last_cost_usd"] is not None else None,
        "is_idle": row["is_idle"],
        "idle_since": row["idle_since"].isoformat() if row["idle_since"] else None,
        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
    }
