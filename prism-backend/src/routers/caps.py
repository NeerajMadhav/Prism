"""Budget cap routes."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.schemas.caps import CapCreateRequest, CapUpdateRequest
from src.types.models import UserContext
from src.utils.date_utils import current_month_start, utc_now
from src.utils.errors import AppError
from src.workers.alerts_worker import check_org_alerts

router = APIRouter(prefix="/v1/orgs/{org_id}/caps", tags=["caps"])


async def _cap_spend(db: asyncpg.Connection, org_id: UUID, cap: asyncpg.Record) -> float:
    month_start = current_month_start()
    if cap["scope"] == "platform":
        val = await db.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0) FROM cost_records
            WHERE org_id = $1 AND provider = $2 AND time::date >= $3
            """,
            org_id,
            cap["scope_value"],
            month_start,
        )
    elif cap["scope"] == "service":
        val = await db.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0) FROM cost_records
            WHERE org_id = $1 AND service = $2 AND time::date >= $3
            """,
            org_id,
            cap["scope_value"],
            month_start,
        )
    else:
        val = await db.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0) FROM cost_records
            WHERE org_id = $1 AND account_id = $2::uuid AND time::date >= $3
            """,
            org_id,
            cap["scope_value"],
            month_start,
        )
    return float(val or 0)


def _serialize(cap: asyncpg.Record, spend: float | None = None) -> dict:
    pct = None
    if spend is not None and cap["cap_amount"]:
        pct = spend / float(cap["cap_amount"]) * 100
    return {
        "id": str(cap["id"]),
        "name": cap["name"],
        "scope": cap["scope"],
        "scope_value": cap["scope_value"],
        "cap_amount": float(cap["cap_amount"]),
        "period": cap["period"],
        "is_active": cap["is_active"],
        "created_at": cap["created_at"].isoformat(),
        "updated_at": cap["updated_at"].isoformat(),
        "current_month_spend": spend,
        "pct_used": pct,
    }


@router.get("/")
async def list_caps(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    caps = await db.fetch(
        """
        SELECT * FROM budget_caps
        WHERE org_id = $1 AND is_active = TRUE AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        org["id"],
    )
    result = []
    for cap in caps:
        spend = await _cap_spend(db, org["id"], cap)
        result.append(_serialize(cap, spend))
    return result


@router.post("/", status_code=201)
async def create_cap(
    body: CapCreateRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO budget_caps (org_id, name, scope, scope_value, cap_amount, period)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        org["id"],
        body.name,
        body.scope,
        body.scope_value,
        body.cap_amount,
        body.period,
    )
    check_org_alerts.delay(str(org["id"]))
    return _serialize(row, 0.0)


@router.get("/{cap_id}")
async def get_cap(
    cap_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    cap = await db.fetchrow(
        """
        SELECT * FROM budget_caps
        WHERE id = $1 AND org_id = $2 AND deleted_at IS NULL
        """,
        cap_id,
        org["id"],
    )
    if cap is None:
        raise AppError("Cap not found", status_code=404)
    spend = await _cap_spend(db, org["id"], cap)
    history = await db.fetch(
        """
        SELECT id, type, severity, threshold_percent, triggered_at
        FROM alerts WHERE cap_id = $1 ORDER BY triggered_at DESC LIMIT 20
        """,
        cap_id,
    )
    data = _serialize(cap, spend)
    data["alert_history"] = [
        {
            "id": str(h["id"]),
            "type": h["type"],
            "severity": h["severity"],
            "threshold_percent": float(h["threshold_percent"])
            if h["threshold_percent"] is not None
            else None,
            "triggered_at": h["triggered_at"].isoformat(),
        }
        for h in history
    ]
    return data


@router.put("/{cap_id}")
async def update_cap(
    cap_id: UUID,
    body: CapUpdateRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    cap = await db.fetchrow(
        """
        UPDATE budget_caps
        SET name = COALESCE($3, name),
            cap_amount = COALESCE($4, cap_amount),
            is_active = COALESCE($5, is_active),
            updated_at = NOW()
        WHERE id = $1 AND org_id = $2 AND deleted_at IS NULL
        RETURNING *
        """,
        cap_id,
        org["id"],
        body.name,
        body.cap_amount,
        body.is_active,
    )
    if cap is None:
        raise AppError("Cap not found", status_code=404)
    spend = await _cap_spend(db, org["id"], cap)
    return _serialize(cap, spend)


@router.delete("/{cap_id}")
async def delete_cap(
    cap_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute(
        """
        UPDATE budget_caps
        SET is_active = FALSE, deleted_at = $3
        WHERE id = $1 AND org_id = $2
        """,
        cap_id,
        org["id"],
        utc_now(),
    )
    return {"message": "Cap deleted"}
