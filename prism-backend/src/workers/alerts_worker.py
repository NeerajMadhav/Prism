"""Celery task: run cap alert checks for an org."""

import asyncio
from uuid import UUID

from src.services.alert_service import CapAlertService
from src.workers.celery_app import celery_app


@celery_app.task(name="prism-alerts.check_org", bind=True, max_retries=3)
def check_org_alerts(self, org_id: str) -> dict[str, int]:
    created = asyncio.run(CapAlertService().check_org(UUID(org_id)))
    return {"alerts_created": created}
