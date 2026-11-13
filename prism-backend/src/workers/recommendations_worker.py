"""Celery tasks: recommendation generation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.recommendation_service import RecommendationService
from src.workers import run_async_db
from src.workers.celery_app import celery_app


@celery_app.task(name="prism-recommendations.run", max_retries=3)
def run_recommendations(org_id: str) -> int:
    return run_async_db(lambda conn: RecommendationService.generate_for_org(conn, UUID(org_id)))


@celery_app.task(name="prism-recommendations.schedule_daily")
def schedule_daily_recommendations() -> int:
    async def _run(conn: Any) -> int:
        rows = await conn.fetch("SELECT id FROM organizations")
        for row in rows:
            run_recommendations.apply_async(kwargs={"org_id": str(row["id"])})
        return len(rows)

    return run_async_db(_run)
