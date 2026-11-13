"""Celery tasks: commitment sync."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.commitment_service import CommitmentService
from src.workers import run_async_db
from src.workers.celery_app import celery_app


@celery_app.task(name="prism-commitments.run", max_retries=3)
def run_commitments(org_id: str) -> int:
    return run_async_db(lambda conn: CommitmentService.sync_for_org(conn, UUID(org_id)))


@celery_app.task(name="prism-commitments.schedule_daily")
def schedule_daily_commitments() -> int:
    async def _run(conn: Any) -> int:
        rows = await conn.fetch("SELECT id FROM organizations")
        for row in rows:
            run_commitments.apply_async(kwargs={"org_id": str(row["id"])})
        return len(rows)

    return run_async_db(_run)
