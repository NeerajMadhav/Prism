"""Cost aggregation endpoints with Redis caching."""

from __future__ import annotations

import json
from datetime import date, timedelta

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.config.database import get_db
from src.config.redis_client import get_redis, redis_get, redis_set
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.date_utils import current_month_start, iter_days, next_month_start, utc_now
from src.utils.errors import AppError
from src.utils.pagination import get_pagination, paginated_response

router = APIRouter(prefix="/v1/orgs/{org_id}/costs", tags=["costs"])

CACHE_TTL = 300

# All providers store one UTC calendar-day bucket per service/region.
_DAY_BASIS = "UTC calendar day (00:00 UTC)"
_GRANULARITY = "day"


def _parse_month(month: str | None) -> str:
    if not month:
        return current_month_start().strftime("%Y-%m")
    if len(month) != 7 or month[4] != "-":
        raise AppError("month must be YYYY-MM", status_code=400)
    return month


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    start = date(year, mon, 1)
    end = next_month_start(start)
    return start, end


def _cost_column(view: str) -> str:
    if view == "amortized":
        return "cost_amortized_usd"
    return "cost_unblended_usd"


async def _cache_get(_redis: object, key: str) -> dict | list | None:
    raw = await redis_get(key)
    if not raw:
        return None
    return json.loads(raw)


async def _cache_set(_redis: object, key: str, value: dict | list) -> None:
    await redis_set(key, json.dumps(value, default=str), ex=CACHE_TTL)


@router.get("")
async def overall_costs(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
    redis=Depends(get_redis),
    month: str | None = Query(default=None),
    view: str = Query(default="unblended"),
) -> dict:
    month_s = _parse_month(month)
    cache_key = f"dash:{org['id']}:overall:{month_s}:{view}"
    cached = await _cache_get(redis, cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    col = _cost_column(view)
    start, end = _month_bounds(month_s)
    prev_start = date(start.year - 1, start.month, 1) if start.month == 1 else date(start.year, start.month - 1, 1)
    prev_end = start

    by_provider = await db.fetch(
        f"""
        SELECT provider,
               SUM({col}) AS total_usd,
               SUM(cost_amortized_usd) AS total_amortized_usd,
               COUNT(DISTINCT account_id) AS account_count,
               COUNT(DISTINCT service) AS service_count
        FROM cost_records
        WHERE org_id = $1 AND time >= $2 AND time < $3
        GROUP BY provider
        ORDER BY provider
        """,
        org["id"],
        start,
        end,
    )
    total = await db.fetchval(
        f"SELECT COALESCE(SUM({col}), 0) FROM cost_records WHERE org_id = $1 AND time >= $2 AND time < $3",
        org["id"],
        start,
        end,
    )
    total_amortized = await db.fetchval(
        """
        SELECT COALESCE(SUM(cost_amortized_usd), 0)
        FROM cost_records WHERE org_id = $1 AND time >= $2 AND time < $3
        """,
        org["id"],
        start,
        end,
    )
    prev_total = await db.fetchval(
        f"""
        SELECT COALESCE(SUM({col}), 0) FROM cost_records
        WHERE org_id = $1 AND time >= $2 AND time < $3
        """,
        org["id"],
        prev_start,
        prev_end,
    )

    data_as_of = await db.fetchval(
        "SELECT MAX(data_as_of) FROM cloud_accounts WHERE org_id = $1 AND is_active = TRUE",
        org["id"],
    )
    payload = {
        "month": month_s,
        "granularity": _GRANULARITY,
        "timezone": org.get("timezone") or "UTC",
        "billing_day_basis": _DAY_BASIS,
        "view": view,
        "data_as_of": data_as_of.isoformat() if data_as_of else None,
        "by_provider": [
            {
                "provider": r["provider"],
                "total_usd": float(r["total_usd"] or 0),
                "total_amortized_usd": float(r["total_amortized_usd"] or 0),
                "account_count": int(r["account_count"] or 0),
                "service_count": int(r["service_count"] or 0),
            }
            for r in by_provider
        ],
        "total_usd": float(total or 0),
        "total_amortized_usd": float(total_amortized or 0),
        "prev_month_total_usd": float(prev_total or 0),
    }
    await _cache_set(redis, cache_key, payload)
    return payload


@router.get("/by-service")
async def costs_by_service(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
    redis=Depends(get_redis),
    month: str | None = Query(default=None),
    view: str = Query(default="unblended"),
    provider: str | None = Query(default=None),
) -> dict:
    month_s = _parse_month(month)
    cache_key = f"dash:{org['id']}:by-service:{month_s}:{view}:{provider or 'all'}"
    cached = await _cache_get(redis, cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    col = _cost_column(view)
    start, end = _month_bounds(month_s)
    prev_start = date(start.year, start.month - 1, 1) if start.month > 1 else date(start.year - 1, 12, 1)
    pg = get_pagination(request)

    if provider:
        total = await db.fetchval(
            """
            SELECT COUNT(*) FROM (
              SELECT service, provider FROM cost_records
              WHERE org_id = $1 AND time >= $2 AND time < $3 AND provider = $4
              GROUP BY service, provider
            ) s
            """,
            org["id"],
            start,
            end,
            provider,
        )
        rows = await db.fetch(
            f"""
            WITH current AS (
              SELECT service, provider, SUM({col}) AS total_usd
              FROM cost_records
              WHERE org_id = $1 AND time >= $2 AND time < $3 AND provider = $4
              GROUP BY service, provider
            ),
            previous AS (
              SELECT service, provider, SUM({col}) AS prev_total
              FROM cost_records
              WHERE org_id = $1 AND time >= $5 AND time < $3 AND provider = $4
              GROUP BY service, provider
            )
            SELECT c.service, c.provider, c.total_usd, COALESCE(p.prev_total, 0) AS prev_month_usd
            FROM current c
            LEFT JOIN previous p ON p.service = c.service AND p.provider = c.provider
            ORDER BY c.total_usd DESC
            LIMIT $6 OFFSET $7
            """,
            org["id"],
            start,
            end,
            provider,
            prev_start,
            pg["limit"],
            pg["offset"],
        )
    else:
        total = await db.fetchval(
            """
            SELECT COUNT(*) FROM (
              SELECT service, provider FROM cost_records
              WHERE org_id = $1 AND time >= $2 AND time < $3
              GROUP BY service, provider
            ) s
            """,
            org["id"],
            start,
            end,
        )
        rows = await db.fetch(
            f"""
            WITH current AS (
              SELECT service, provider, SUM({col}) AS total_usd
              FROM cost_records
              WHERE org_id = $1 AND time >= $2 AND time < $3
              GROUP BY service, provider
            ),
            previous AS (
              SELECT service, provider, SUM({col}) AS prev_total
              FROM cost_records
              WHERE org_id = $1 AND time >= $4 AND time < $3
              GROUP BY service, provider
            )
            SELECT c.service, c.provider, c.total_usd, COALESCE(p.prev_total, 0) AS prev_month_usd
            FROM current c
            LEFT JOIN previous p ON p.service = c.service AND p.provider = c.provider
            ORDER BY c.total_usd DESC
            LIMIT $5 OFFSET $6
            """,
            org["id"],
            start,
            end,
            prev_start,
            pg["limit"],
            pg["offset"],
        )
    data = []
    for r in rows:
        cur = float(r["total_usd"] or 0)
        prev = float(r["prev_month_usd"] or 0)
        change_pct = ((cur - prev) / prev * 100) if prev > 0 else None
        data.append(
            {
                "service": r["service"],
                "provider": r["provider"],
                "total_usd": cur,
                "prev_month_usd": prev,
                "change_pct": change_pct,
            }
        )
    result = paginated_response(data, int(total or 0), pg["page"], pg["limit"])
    await _cache_set(redis, cache_key, result)
    return result


@router.get("/by-day")
async def costs_by_day(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
    redis=Depends(get_redis),
    month: str | None = Query(default=None),
    view: str = Query(default="unblended"),
) -> dict:
    """Day-wise spend for the month — one entry per calendar day (zeros filled).

    AWS/Azure/GCP are all stored as UTC day buckets so series are comparable.
    """
    month_s = _parse_month(month)
    cache_key = f"dash:{org['id']}:by-day:v2:{month_s}:{view}"
    cached = await _cache_get(redis, cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    col = _cost_column(view)
    start, end = _month_bounds(month_s)
    # Cap chart series at today for the current month (no future zero noise).
    today = utc_now().date()
    if start.year == today.year and start.month == today.month:
        series_end = min(end, today + timedelta(days=1))
    else:
        series_end = end

    rows = await db.fetch(
        f"""
        SELECT DATE(time AT TIME ZONE 'UTC') AS day,
               provider,
               SUM({col}) AS total_usd,
               BOOL_OR(is_estimate) AS has_estimates
        FROM cost_records
        WHERE org_id = $1 AND time >= $2 AND time < $3
        GROUP BY day, provider
        ORDER BY day
        """,
        org["id"],
        start,
        end,
    )
    by_day: dict[str, dict] = {}
    providers: set[str] = set()
    for r in rows:
        day = r["day"].isoformat()
        entry = by_day.setdefault(
            day,
            {
                "date": day,
                "total_usd": 0.0,
                "by_provider": {},
                "has_estimates": False,
                "has_data": True,
            },
        )
        amt = float(r["total_usd"] or 0)
        entry["total_usd"] += amt
        provider = r["provider"]
        providers.add(provider)
        entry["by_provider"][provider] = entry["by_provider"].get(provider, 0.0) + amt
        if r["has_estimates"]:
            entry["has_estimates"] = True

    days_out: list[dict] = []
    for d in iter_days(start, series_end):
        key = d.isoformat()
        if key in by_day:
            days_out.append(by_day[key])
        else:
            days_out.append(
                {
                    "date": key,
                    "total_usd": 0.0,
                    "by_provider": {},
                    "has_estimates": False,
                    "has_data": False,
                }
            )

    data_as_of = await db.fetchval(
        "SELECT MAX(data_as_of) FROM cloud_accounts WHERE org_id = $1 AND is_active = TRUE",
        org["id"],
    )
    payload = {
        "month": month_s,
        "granularity": _GRANULARITY,
        "timezone": "UTC",
        "billing_day_basis": _DAY_BASIS,
        "view": view,
        "data_as_of": data_as_of.isoformat() if data_as_of else None,
        "providers": sorted(providers),
        "days": days_out,
    }
    await _cache_set(redis, cache_key, payload)
    return payload


@router.get("/by-tag")
async def costs_by_tag(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
    redis=Depends(get_redis),
    month: str | None = Query(default=None),
    tag_key: str = Query(...),
    view: str = Query(default="unblended"),
) -> list[dict]:
    month_s = _parse_month(month)
    key = tag_key.lower().strip()
    cache_key = f"dash:{org['id']}:by-tag:{month_s}:{key}:{view}"
    cached = await _cache_get(redis, cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    col = _cost_column(view)
    start, end = _month_bounds(month_s)
    rows = await db.fetch(
        f"""
        SELECT COALESCE(tags->>$4, '(untagged)') AS tag_value, SUM({col}) AS total_usd
        FROM cost_records
        WHERE org_id = $1 AND time >= $2 AND time < $3
        GROUP BY tag_value
        ORDER BY total_usd DESC
        """,
        org["id"],
        start,
        end,
        key,
    )
    grand = sum(float(r["total_usd"] or 0) for r in rows)
    data = [
        {
            "tag_value": r["tag_value"],
            "total_usd": float(r["total_usd"] or 0),
            "pct_of_total": (float(r["total_usd"] or 0) / grand * 100) if grand > 0 else 0.0,
        }
        for r in rows
    ]
    await _cache_set(redis, cache_key, data)
    return data


@router.get("/top-services")
async def top_services(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
    redis=Depends(get_redis),
    month: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    view: str = Query(default="unblended"),
) -> list[dict]:
    month_s = _parse_month(month)
    cache_key = f"dash:{org['id']}:top-services:{month_s}:{limit}:{view}"
    cached = await _cache_get(redis, cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    col = _cost_column(view)
    start, end = _month_bounds(month_s)
    rows = await db.fetch(
        f"""
        SELECT service, provider, SUM({col}) AS total_usd
        FROM cost_records
        WHERE org_id = $1 AND time >= $2 AND time < $3
        GROUP BY service, provider
        ORDER BY total_usd DESC
        LIMIT $4
        """,
        org["id"],
        start,
        end,
        limit,
    )
    data = [
        {
            "service": r["service"],
            "provider": r["provider"],
            "total_usd": float(r["total_usd"] or 0),
            "rank": idx + 1,
        }
        for idx, r in enumerate(rows)
    ]
    await _cache_set(redis, cache_key, data)
    return data
