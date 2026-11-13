"""Commitment tracking routes."""

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.pagination import get_pagination, paginated_response

router = APIRouter(prefix="/v1/orgs/{org_id}/commitments", tags=["commitments"])


@router.get("/")
async def list_commitments(
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
    if request.query_params.get("status"):
        args.append(request.query_params["status"])
        filters.append(f"status = ${len(args)}")
    where = " AND ".join(filters)
    total = await db.fetchval(f"SELECT COUNT(*) FROM commitment_records WHERE {where}", *args)
    rows = await db.fetch(
        f"""
        SELECT * FROM commitment_records WHERE {where}
        ORDER BY end_date ASC NULLS LAST
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        params["limit"],
        params["offset"],
    )
    data = [_serialize(r) for r in rows]
    return paginated_response(data, int(total or 0), params["page"], params["limit"])


@router.get("/summary")
async def commitment_summary(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    totals = await db.fetchrow(
        """
        SELECT
          COALESCE(SUM(monthly_cost), 0) AS total_monthly_cost,
          COALESCE(AVG(utilization_pct), 0) AS avg_utilization_pct,
          COALESCE(AVG(coverage_pct), 0) AS avg_coverage_pct
        FROM commitment_records
        WHERE org_id = $1 AND status = 'active'
        """,
        org["id"],
    )
    by_provider = await db.fetch(
        """
        SELECT provider,
               COALESCE(SUM(monthly_cost), 0) AS monthly_cost,
               COALESCE(AVG(utilization_pct), 0) AS utilization_pct
        FROM commitment_records
        WHERE org_id = $1 AND status = 'active'
        GROUP BY provider
        """,
        org["id"],
    )
    return {
        "total_monthly_cost": float(totals["total_monthly_cost"]),
        "avg_utilization_pct": float(totals["avg_utilization_pct"]),
        "avg_coverage_pct": float(totals["avg_coverage_pct"]),
        "by_provider": [
            {
                "provider": r["provider"],
                "monthly_cost": float(r["monthly_cost"]),
                "utilization_pct": float(r["utilization_pct"]),
            }
            for r in by_provider
        ],
    }


@router.get("/expiring")
async def expiring_commitments(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    days = int(request.query_params.get("days", "30"))
    rows = await db.fetch(
        """
        SELECT * FROM commitment_records
        WHERE org_id = $1
          AND end_date IS NOT NULL
          AND end_date <= CURRENT_DATE + $2::int
          AND status IN ('active', 'expiring_soon')
        ORDER BY end_date ASC
        """,
        org["id"],
        days,
    )
    return [_serialize(r) for r in rows]


def _serialize(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "provider": row["provider"],
        "commitment_type": row["commitment_type"],
        "resource_type": row["resource_type"],
        "arn_or_id": row["arn_or_id"],
        "start_date": row["start_date"].isoformat() if row["start_date"] else None,
        "end_date": row["end_date"].isoformat() if row["end_date"] else None,
        "monthly_cost": float(row["monthly_cost"] or 0) if row["monthly_cost"] is not None else None,
        "utilization_pct": float(row["utilization_pct"] or 0)
        if row["utilization_pct"] is not None
        else None,
        "coverage_pct": float(row["coverage_pct"] or 0) if row["coverage_pct"] is not None else None,
        "status": row["status"],
    }
