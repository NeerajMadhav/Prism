"""Alert list and acknowledge routes."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.schemas.alerts import SnoozeRequest
from src.types.models import UserContext
from src.utils.date_utils import utc_now
from src.utils.errors import AppError
from src.utils.pagination import get_pagination, paginated_response

router = APIRouter(prefix="/v1/orgs/{org_id}/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    params = get_pagination(request)
    filters = ["org_id = $1"]
    args: list = [org["id"]]
    for key in ("type", "severity"):
        if request.query_params.get(key):
            args.append(request.query_params[key])
            filters.append(f"{key} = ${len(args)}")
    if request.query_params.get("acknowledged") == "false":
        filters.append("acknowledged_at IS NULL")
    where = " AND ".join(filters)
    total = await db.fetchval(f"SELECT COUNT(*) FROM alerts WHERE {where}", *args)
    rows = await db.fetch(
        f"""
        SELECT * FROM alerts WHERE {where}
        ORDER BY triggered_at DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        params["limit"],
        params["offset"],
    )
    data = [_serialize(r) for r in rows]
    return paginated_response(data, int(total or 0), params["page"], params["limit"])


@router.get("/count")
async def alert_count(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Return active (unacknowledged, not currently snoozed) alert count for badge polling."""
    active = await db.fetchval(
        """
        SELECT COUNT(*)
        FROM alerts
        WHERE org_id = $1
          AND acknowledged_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until <= NOW())
        """,
        org["id"],
    )
    return {"active": int(active or 0)}


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    org: dict = Depends(get_org_access),
    current_user: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        """
        UPDATE alerts
        SET acknowledged_at = $3, acknowledged_by = $4
        WHERE id = $1 AND org_id = $2
        RETURNING *
        """,
        alert_id,
        org["id"],
        utc_now(),
        current_user.user_id,
    )
    if row is None:
        raise AppError("Alert not found", status_code=404)
    return _serialize(row)


@router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: UUID,
    body: SnoozeRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        """
        UPDATE alerts SET snoozed_until = $3
        WHERE id = $1 AND org_id = $2
        RETURNING *
        """,
        alert_id,
        org["id"],
        body.snooze_until,
    )
    if row is None:
        raise AppError("Alert not found", status_code=404)
    return _serialize(row)


def _serialize(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "scope": row["scope"],
        "scope_value": row["scope_value"],
        "severity": row["severity"],
        "threshold_percent": float(row["threshold_percent"]) if row["threshold_percent"] is not None else None,
        "message": row["message"],
        "triggered_at": row["triggered_at"].isoformat(),
        "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None,
        "acknowledged_by": str(row["acknowledged_by"]) if row["acknowledged_by"] else None,
        "snoozed_until": row["snoozed_until"].isoformat() if row["snoozed_until"] else None,
        "cap_id": str(row["cap_id"]) if row["cap_id"] else None,
    }
