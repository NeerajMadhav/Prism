"""Cost optimization recommendation routes."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.pagination import get_pagination, paginated_response

router = APIRouter(prefix="/v1/orgs/{org_id}/recommendations", tags=["recommendations"])


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(implemented|rejected|archived)$")


@router.get("/")
async def list_recommendations(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    params = get_pagination(request)
    filters = ["org_id = $1"]
    args: list = [org["id"]]
    if request.query_params.get("type"):
        args.append(request.query_params["type"])
        filters.append(f"type = ${len(args)}")
    if request.query_params.get("status"):
        args.append(request.query_params["status"])
        filters.append(f"status = ${len(args)}")
    else:
        args.append("open")
        filters.append(f"status = ${len(args)}")
    if request.query_params.get("provider"):
        args.append(request.query_params["provider"])
        filters.append(f"metadata->>'provider' = ${len(args)}")
    where = " AND ".join(filters)
    total = await db.fetchval(f"SELECT COUNT(*) FROM recommendations WHERE {where}", *args)
    rows = await db.fetch(
        f"""
        SELECT * FROM recommendations WHERE {where}
        ORDER BY savings_usd DESC NULLS LAST
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        params["limit"],
        params["offset"],
    )
    data = [
        {
            "id": str(r["id"]),
            "type": r["type"],
            "title": r["title"],
            "description": r["description"],
            "savings_usd": float(r["savings_usd"] or 0),
            "confidence": r["confidence"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    return paginated_response(data, int(total or 0), params["page"], params["limit"])


@router.put("/{rec_id}/status")
async def update_status(
    rec_id: UUID,
    body: RecommendationStatusUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        """
        UPDATE recommendations
        SET status = $3, updated_at = NOW()
        WHERE id = $1 AND org_id = $2
        RETURNING *
        """,
        rec_id,
        org["id"],
        body.status,
    )
    if row is None:
        raise AppError("Recommendation not found", status_code=404)
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "title": row["title"],
    }
