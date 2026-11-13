"""Celery tasks: monthly reports."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.report_service import ReportService
from src.workers import run_async_db
from src.workers.celery_app import celery_app


@celery_app.task(name="prism-reports.send", max_retries=3)
def send_report(org_id: str, force: bool = False) -> bool:
    return run_async_db(
        lambda conn: ReportService.generate(conn, UUID(org_id), force=force)
    )


@celery_app.task(name="prism-reports.schedule_daily")
def schedule_daily_reports() -> int:
    async def _run(conn: Any) -> int:
        rows = await conn.fetch(
            """
            SELECT org_id FROM monthly_reports
            WHERE is_active = TRUE
              AND next_send IS NOT NULL
              AND date_trunc('day', next_send) <= date_trunc('day', NOW())
            """
        )
        for row in rows:
            send_report.apply_async(kwargs={"org_id": str(row["org_id"]), "force": False})
        return len(rows)

    return run_async_db(_run)
