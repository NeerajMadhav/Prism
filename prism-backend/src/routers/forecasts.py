"""Spend forecast routes."""

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.date_utils import current_month_start

router = APIRouter(prefix="/v1/orgs/{org_id}/forecasts", tags=["forecasts"])


@router.get("/")
async def get_forecast(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict | list:
    month = request.query_params.get("month")
    month_start = current_month_start()
    if month:
        year, mon = month.split("-")
        month_start = month_start.replace(year=int(year), month=int(mon))
    provider = request.query_params.get("provider", "all")
    if provider == "all":
        rows = await db.fetch(
            """
            SELECT * FROM spend_forecasts
            WHERE org_id = $1 AND forecast_month = $2
            ORDER BY provider
            """,
            org["id"],
            month_start,
        )
        return [_row(r) for r in rows]
    row = await db.fetchrow(
        """
        SELECT * FROM spend_forecasts
        WHERE org_id = $1 AND forecast_month = $2 AND provider = $3
        """,
        org["id"],
        month_start,
        provider,
    )
    if row is None:
        return {
            "month": month_start.strftime("%Y-%m"),
            "provider": provider,
            "data_coverage": "insufficient",
            "projected_total": None,
        }
    return _row(row)


def _row(row: asyncpg.Record) -> dict:
    projected = row["projected_total"]
    return {
        "month": row["forecast_month"].strftime("%Y-%m"),
        "provider": row["provider"],
        "daily_avg": float(row["daily_avg"] or 0) if row["daily_avg"] is not None else None,
        "projected_total": float(projected) if projected is not None else None,
        "cap_amount": float(row["cap_amount"] or 0) if row["cap_amount"] is not None else None,
        "will_breach": row["will_breach"],
        "days_elapsed": row["days_elapsed"],
        "days_with_data": row["days_with_data"],
        "data_coverage": row["data_coverage"],
        "computed_at": row["computed_at"].isoformat(),
    }


@router.get("/history")
async def forecast_history(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT forecast_month AS month, projected_total, actual_total, variance_pct
        FROM spend_forecasts
        WHERE org_id = $1 AND actual_total IS NOT NULL
        ORDER BY forecast_month DESC
        LIMIT 12
        """,
        org["id"],
    )
    return [
        {
            "month": r["month"].strftime("%Y-%m"),
            "projected_total": float(r["projected_total"] or 0),
            "actual_total": float(r["actual_total"] or 0),
            "variance_pct": float(r["variance_pct"] or 0) if r["variance_pct"] is not None else None,
        }
        for r in rows
    ]
