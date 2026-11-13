"""Celery tasks: spend forecasts and accuracy."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.services.forecast_service import ForecastService
from src.workers.celery_app import celery_app


@celery_app.task(name="prism-forecast.run", max_retries=3)
def run_forecast(org_id: str) -> int:
    async def _run() -> int:
        from src.config.database import get_pool

        pool = get_pool()
        async with pool.acquire() as db:
            return await ForecastService.compute_for_org(db, UUID(org_id))

    return asyncio.run(_run())


@celery_app.task(name="prism-forecast.schedule_daily")
def schedule_daily_forecast() -> int:
    async def _run(conn: Any) -> int:
        rows = await conn.fetch("SELECT id FROM organizations")
        for row in rows:
            run_forecast.apply_async(kwargs={"org_id": str(row["id"])})
        return len(rows)

    from src.workers import run_async_db

    return run_async_db(_run)


@celery_app.task(name="prism-forecast.compute_accuracy")
def compute_forecast_accuracy() -> int:
    from src.workers import run_async_db

    return run_async_db(lambda conn: ForecastService.compute_forecast_accuracy(conn))
