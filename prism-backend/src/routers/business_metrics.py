"""Business metrics and unit economics routes."""

import json
from datetime import date, timedelta
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.config.redis_client import redis_get, redis_set
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.date_utils import current_month_start, utc_now
from src.utils.errors import AppError

router = APIRouter(prefix="/v1/orgs/{org_id}/metrics", tags=["business-metrics"])


class MetricCreate(BaseModel):
    name: str
    source: str = "manual"
    unit: str


class MetricValuesIngest(BaseModel):
    values: list[dict] = Field(max_length=1000)


@router.get("/")
async def list_metrics(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM business_metrics WHERE org_id = $1 AND is_active = TRUE ORDER BY name",
        org["id"],
    )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "source": r["source"],
            "unit": r["unit"],
        }
        for r in rows
    ]


@router.post("/", status_code=201)
async def create_metric(
    body: MetricCreate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    try:
        row = await db.fetchrow(
            """
            INSERT INTO business_metrics (org_id, name, source, unit)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            org["id"],
            body.name,
            body.source,
            body.unit,
        )
    except asyncpg.UniqueViolationError as exc:
        raise AppError("Metric name already exists", status_code=409) from exc
    return {"id": str(row["id"]), "name": row["name"], "source": row["source"], "unit": row["unit"]}


@router.delete("/{metric_id}")
async def delete_metric(
    metric_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute(
        "UPDATE business_metrics SET is_active = FALSE WHERE id = $1 AND org_id = $2",
        metric_id,
        org["id"],
    )
    return {"message": "Metric deactivated"}


@router.post("/{metric_id}/values")
async def ingest_values(
    metric_id: UUID,
    body: MetricValuesIngest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    if len(body.values) > 1000:
        raise AppError("Max 1000 values per request", status_code=400)
    for entry in body.values:
        day = entry["date"]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        await db.execute(
            """
            INSERT INTO business_metric_values (metric_id, org_id, date, value)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (metric_id, date) DO UPDATE SET value = EXCLUDED.value
            """,
            metric_id,
            org["id"],
            day,
            float(entry["value"]),
        )
    return {"message": f"Ingested {len(body.values)} values"}


@router.get("/{metric_id}/values")
async def metric_values(
    metric_id: UUID,
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    days = min(int(request.query_params.get("days", "30")), 365)
    since = utc_now().date() - timedelta(days=days)
    rows = await db.fetch(
        """
        SELECT date, value FROM business_metric_values
        WHERE metric_id = $1 AND org_id = $2 AND date >= $3
        ORDER BY date
        """,
        metric_id,
        org["id"],
        since,
    )
    return [{"date": r["date"].isoformat(), "value": float(r["value"])} for r in rows]


@router.get("/unit-economics")
async def unit_economics(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    month = request.query_params.get("month")
    month_start = current_month_start()
    if month:
        year, mon = month.split("-")
        month_start = month_start.replace(year=int(year), month=int(mon))
    cache_key = f"unit:econ:{org['id']}:{month_start.strftime('%Y-%m')}"
    cached = await redis_get(cache_key)
    if cached:
        return json.loads(cached)

    metrics = await db.fetch(
        "SELECT id, name, unit FROM business_metrics WHERE org_id = $1 AND is_active = TRUE",
        org["id"],
    )
    cloud_total = float(
        await db.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0) FROM cost_records
            WHERE org_id = $1 AND time::date >= $2
            """,
            org["id"],
            month_start,
        )
        or 0
    )
    results = []
    for metric in metrics:
        metric_total = float(
            await db.fetchval(
                """
                SELECT COALESCE(SUM(value), 0) FROM business_metric_values
                WHERE metric_id = $1 AND date >= $2 AND date < $3::date + INTERVAL '1 month'
                """,
                metric["id"],
                month_start,
                month_start,
            )
            or 0
        )
        cost_per_unit = cloud_total / metric_total if metric_total > 0 else None
        results.append(
            {
                "metric_name": metric["name"],
                "unit": metric["unit"],
                "metric_total": metric_total,
                "cloud_total": cloud_total,
                "cost_per_unit": cost_per_unit,
                "trend_30d": None,
                "trend_90d": None,
            }
        )
    await redis_set(cache_key, json.dumps(results), ex=900)
    return results
