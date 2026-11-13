"""Notification channel settings."""

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.services.email_service import EmailService
from src.types.models import UserContext
from src.utils.logger import get_logger
from src.utils.validate_webhook_url import validate_webhook_url, verify_dispatch_url

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/orgs/{org_id}/notifications", tags=["notifications"])
email_service = EmailService()


class NotificationSettingsUpdate(BaseModel):
    alert_emails: list[str] | None = None
    teams_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    alert_threshold_75: bool | None = None
    alert_threshold_90: bool | None = None
    alert_threshold_100: bool | None = None
    alert_threshold_125: bool | None = None
    alert_threshold_150: bool | None = None


def _mask_url(url: str | None) -> str | None:
    if not url:
        return None
    return f"{url[:5]}***"


@router.get("/")
async def get_notifications(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow("SELECT * FROM notification_settings WHERE org_id = $1", org["id"])
    if row is None:
        row = await db.fetchrow(
            "INSERT INTO notification_settings (org_id) VALUES ($1) RETURNING *",
            org["id"],
        )
    return {
        "alert_emails": row["alert_emails"] or [],
        "teams_webhook_url": _mask_url(row["teams_webhook_url"]),
        "slack_webhook_url": _mask_url(row["slack_webhook_url"]),
        "alert_threshold_75": row["alert_threshold_75"],
        "alert_threshold_90": row["alert_threshold_90"],
        "alert_threshold_100": row["alert_threshold_100"],
        "alert_threshold_125": row["alert_threshold_125"],
        "alert_threshold_150": row["alert_threshold_150"],
    }


@router.put("/")
async def update_notifications(
    body: NotificationSettingsUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    if body.teams_webhook_url:
        validate_webhook_url(body.teams_webhook_url)
    if body.slack_webhook_url:
        validate_webhook_url(body.slack_webhook_url)
    row = await db.fetchrow(
        """
        INSERT INTO notification_settings (
          org_id, alert_emails, teams_webhook_url, slack_webhook_url,
          alert_threshold_75, alert_threshold_90, alert_threshold_100,
          alert_threshold_125, alert_threshold_150
        ) VALUES (
          $1, COALESCE($2::text[], '{}'::text[]), $3, $4,
          COALESCE($5,TRUE), COALESCE($6,TRUE), COALESCE($7,TRUE),
          COALESCE($8,TRUE), COALESCE($9,TRUE)
        )
        ON CONFLICT (org_id) DO UPDATE SET
          alert_emails = COALESCE($2::text[], notification_settings.alert_emails),
          teams_webhook_url = COALESCE($3, notification_settings.teams_webhook_url),
          slack_webhook_url = COALESCE($4, notification_settings.slack_webhook_url),
          alert_threshold_75 = COALESCE($5, notification_settings.alert_threshold_75),
          alert_threshold_90 = COALESCE($6, notification_settings.alert_threshold_90),
          alert_threshold_100 = COALESCE($7, notification_settings.alert_threshold_100),
          alert_threshold_125 = COALESCE($8, notification_settings.alert_threshold_125),
          alert_threshold_150 = COALESCE($9, notification_settings.alert_threshold_150)
        RETURNING *
        """,
        org["id"],
        body.alert_emails,
        body.teams_webhook_url,
        body.slack_webhook_url,
        body.alert_threshold_75,
        body.alert_threshold_90,
        body.alert_threshold_100,
        body.alert_threshold_125,
        body.alert_threshold_150,
    )
    return {
        "alert_emails": row["alert_emails"] or [],
        "teams_webhook_url": _mask_url(row["teams_webhook_url"]),
        "slack_webhook_url": _mask_url(row["slack_webhook_url"]),
        "alert_threshold_75": row["alert_threshold_75"],
        "alert_threshold_90": row["alert_threshold_90"],
        "alert_threshold_100": row["alert_threshold_100"],
        "alert_threshold_125": row["alert_threshold_125"],
        "alert_threshold_150": row["alert_threshold_150"],
    }


@router.post("/test/email")
async def test_email(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    settings = await db.fetchrow("SELECT alert_emails FROM notification_settings WHERE org_id = $1", org["id"])
    emails = list(settings["alert_emails"] or []) if settings else []
    if emails:
        email_service._send(emails, "PRISM test alert", "<p>Test</p>", "Test")
    return {"message": "Test email queued"}


@router.post("/test/teams")
async def test_teams(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    settings = await db.fetchrow(
        "SELECT teams_webhook_url FROM notification_settings WHERE org_id = $1",
        org["id"],
    )
    if not settings or not settings["teams_webhook_url"]:
        return {"ok": False, "error": "Teams webhook not configured"}
    url = settings["teams_webhook_url"]
    if not verify_dispatch_url(url):
        return {"ok": False, "error": "Webhook URL failed safety checks"}
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.post(url, json={"text": "PRISM test"})
        if resp.is_redirect:
            return {"ok": False, "error": "Webhook redirects are not allowed"}
        return {"ok": resp.status_code < 300}
    except Exception as exc:
        logger.warning("teams_webhook_test_failed", org_id=str(org["id"]), error=str(exc))
        return {"ok": False, "error": "Webhook test failed"}


@router.post("/test/slack")
async def test_slack(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    settings = await db.fetchrow(
        "SELECT slack_webhook_url FROM notification_settings WHERE org_id = $1",
        org["id"],
    )
    if not settings or not settings["slack_webhook_url"]:
        return {"ok": False, "error": "Slack webhook not configured"}
    url = settings["slack_webhook_url"]
    if not verify_dispatch_url(url):
        return {"ok": False, "error": "Webhook URL failed safety checks"}
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.post(url, json={"text": "PRISM test"})
        if resp.is_redirect:
            return {"ok": False, "error": "Webhook redirects are not allowed"}
        return {"ok": resp.status_code < 300}
    except Exception as exc:
        logger.warning("slack_webhook_test_failed", org_id=str(org["id"]), error=str(exc))
        return {"ok": False, "error": "Webhook test failed"}
