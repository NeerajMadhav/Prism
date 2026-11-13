"""Dead letter queue handler for failed Celery tasks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.email_service import EmailService
from src.utils.logger import get_logger
from src.workers import run_async_db
from src.workers.celery_app import celery_app

logger = get_logger(__name__)
email_service = EmailService()


@celery_app.task(name="prism-dlq.handle")
def handle_dlq(request: Any = None, exc: Any = None, traceback: Any = None) -> None:
    """Log failure and create sync_failure alert."""
    task_name = getattr(getattr(request, "task", None), "name", "unknown")
    kwargs = getattr(request, "kwargs", {}) or {}
    org_id = kwargs.get("org_id")
    account_id = kwargs.get("account_id")
    logger.error(
        "dlq_task",
        task=task_name,
        org_id=org_id,
        account_id=account_id,
        error=str(exc),
    )
    if not org_id:
        return

    async def _run(conn: Any) -> None:
        message = f"Background task {task_name} failed after retries."
        if account_id:
            message += f" Account: {account_id}."
        await conn.execute(
            """
            INSERT INTO alerts (org_id, type, scope_value, severity, message)
            VALUES ($1, 'sync_failure', $2, 'critical', $3)
            """,
            UUID(org_id),
            str(account_id or task_name),
            message[:500],
        )
        settings = await conn.fetchrow(
            "SELECT alert_emails FROM notification_settings WHERE org_id = $1",
            UUID(org_id),
        )
        org = await conn.fetchrow("SELECT name FROM organizations WHERE id = $1", UUID(org_id))
        if settings and settings["alert_emails"]:
            email_service.send_alert_email(
                list(settings["alert_emails"]),
                org["name"] if org else "Organization",
                str(account_id or task_name),
                100.0,
                message,
            )

    run_async_db(_run)
