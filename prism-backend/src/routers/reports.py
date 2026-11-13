"""Monthly report configuration routes."""

from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.date_utils import next_month_start
from src.workers.reports_worker import send_report

router = APIRouter(prefix="/v1/orgs/{org_id}/reports", tags=["reports"])


class ReportConfigUpdate(BaseModel):
    is_active: bool | None = None
    recipient_emails: list[str] | None = None
    send_day: int | None = Field(default=None, ge=1, le=28)
    include_recommendations: bool | None = None
    include_finops_scorecard: bool | None = None
    include_commitments: bool | None = None
    include_unit_economics: bool | None = None


def _serialize(row: asyncpg.Record) -> dict:
    return {
        "is_active": row["is_active"],
        "recipient_emails": row["recipient_emails"] or [],
        "send_day": row["send_day"],
        "next_send": row["next_send"].isoformat() if row["next_send"] else None,
        "last_sent": row["last_sent"].isoformat() if row["last_sent"] else None,
        "include_recommendations": row["include_recommendations"],
        "include_finops_scorecard": row["include_finops_scorecard"],
        "include_commitments": row["include_commitments"],
        "include_unit_economics": row["include_unit_economics"],
    }


@router.get("/")
async def get_report_config(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow("SELECT * FROM monthly_reports WHERE org_id = $1", org["id"])
    if row is None:
        row = await db.fetchrow(
            """
            INSERT INTO monthly_reports (org_id) VALUES ($1)
            RETURNING *
            """,
            org["id"],
        )
    return _serialize(row)  # type: ignore[arg-type]


@router.put("/")
async def update_report_config(
    body: ReportConfigUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    send_day = body.send_day
    next_send = None
    if send_day is not None:
        nxt = next_month_start()
        next_send = datetime(nxt.year, nxt.month, send_day, 9, 0, tzinfo=UTC)
    row = await db.fetchrow(
        """
        INSERT INTO monthly_reports (
          org_id, is_active, recipient_emails, send_day, next_send,
          include_recommendations, include_finops_scorecard, include_commitments,
          include_unit_economics
        ) VALUES ($1, COALESCE($2,FALSE), COALESCE($3::text[], '{}'::text[]), COALESCE($4,1), $5,
          COALESCE($6,TRUE), COALESCE($7,TRUE), COALESCE($8,TRUE), COALESCE($9,FALSE))
        ON CONFLICT (org_id) DO UPDATE SET
          is_active = COALESCE($2, monthly_reports.is_active),
          recipient_emails = COALESCE($3::text[], monthly_reports.recipient_emails),
          send_day = COALESCE($4, monthly_reports.send_day),
          next_send = COALESCE($5, monthly_reports.next_send),
          include_recommendations = COALESCE($6, monthly_reports.include_recommendations),
          include_finops_scorecard = COALESCE($7, monthly_reports.include_finops_scorecard),
          include_commitments = COALESCE($8, monthly_reports.include_commitments),
          include_unit_economics = COALESCE($9, monthly_reports.include_unit_economics)
        RETURNING *
        """,
        org["id"],
        body.is_active,
        body.recipient_emails,
        send_day,
        next_send,
        body.include_recommendations,
        body.include_finops_scorecard,
        body.include_commitments,
        body.include_unit_economics,
    )
    return _serialize(row)  # type: ignore[arg-type]


@router.post("/send-now")
async def send_now(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
) -> dict:
    task = send_report.apply_async(kwargs={"org_id": str(org["id"]), "force": True})
    return {"message": "Report queued", "task_id": task.id}
