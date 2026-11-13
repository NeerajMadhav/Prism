"""Budget cap threshold alerting."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID

import asyncpg
import httpx

from src.config.database import get_pool
from src.services.email_service import EmailService
from src.services.webhook_service import OutboundWebhookService
from src.utils.date_utils import current_month_start
from src.utils.encrypt import aes_decrypt
from src.utils.logger import get_logger

logger = get_logger(__name__)

THRESHOLDS = (75, 90, 100, 125, 150)


class CapAlertService:
    """Evaluate caps for an org and fire notifications."""

    def __init__(self) -> None:
        self.email = EmailService()
        self.webhooks = OutboundWebhookService()

    async def check_org(self, org_id: UUID) -> int:
        """Check all active caps; return count of new alerts created."""
        pool = get_pool()
        created = 0
        async with pool.acquire() as db:
            org = await db.fetchrow("SELECT id, name FROM organizations WHERE id = $1", org_id)
            if not org:
                return 0
            settings = await db.fetchrow(
                "SELECT * FROM notification_settings WHERE org_id = $1",
                org_id,
            )
            caps = await db.fetch(
                """
                SELECT * FROM budget_caps
                WHERE org_id = $1 AND is_active = TRUE AND deleted_at IS NULL
                """,
                org_id,
            )
            month_start = current_month_start()
            for cap in caps:
                spent = await self._cap_spend(db, org_id, cap, month_start)
                if spent is None or cap["cap_amount"] <= 0:
                    continue
                pct = float(spent / Decimal(cap["cap_amount"]) * 100)
                for threshold in THRESHOLDS:
                    if not settings or not settings.get(f"alert_threshold_{threshold}", True):
                        continue
                    if pct < threshold:
                        continue
                    exists = await db.fetchval(
                        """
                        SELECT 1 FROM alerts
                        WHERE org_id = $1 AND cap_id = $2 AND threshold_percent = $3
                          AND type = 'cap_threshold'
                          AND date_trunc('month', triggered_at) = date_trunc('month', NOW()::date)
                        LIMIT 1
                        """,
                        org_id,
                        cap["id"],
                        threshold,
                    )
                    if exists:
                        continue
                    severity = "critical" if threshold >= 100 else "warning"
                    message = (
                        f"{cap['scope_value']} reached {pct:.1f}% of cap "
                        f"({float(spent):.2f} / {float(cap['cap_amount']):.2f})"
                    )
                    alert = await db.fetchrow(
                        """
                        INSERT INTO alerts (
                          org_id, cap_id, type, scope, scope_value, severity,
                          threshold_percent, message
                        )
                        VALUES ($1, $2, 'cap_threshold', $3, $4, $5, $6, $7)
                        RETURNING *
                        """,
                        org_id,
                        cap["id"],
                        cap["scope"],
                        cap["scope_value"],
                        severity,
                        threshold,
                        message,
                    )
                    created += 1
                    await self._fire_channels(db, org, settings, alert, pct)
        return created

    async def _cap_spend(
        self,
        db: asyncpg.Connection,
        org_id: UUID,
        cap: asyncpg.Record,
        month_start,
    ) -> Decimal | None:
        cost_col = "cost_unblended_usd"
        base = """
            SELECT COALESCE(SUM({col}), 0) AS total
            FROM cost_records
            WHERE org_id = $1 AND time >= $2 AND time < ($2::date + INTERVAL '1 month')
        """
        scope = cap["scope"]
        scope_value = cap["scope_value"]
        if scope == "platform":
            sql = base.format(col=cost_col) + " AND provider = $3"
            val = await db.fetchval(sql, org_id, month_start, scope_value)
        elif scope == "service":
            sql = base.format(col=cost_col) + " AND service = $3"
            val = await db.fetchval(sql, org_id, month_start, scope_value)
        elif scope == "account":
            sql = base.format(col=cost_col) + " AND account_id = $3::uuid"
            val = await db.fetchval(sql, org_id, month_start, scope_value)
        else:
            return None
        return Decimal(str(val or 0))

    async def _fire_channels(
        self,
        db: asyncpg.Connection,
        org: asyncpg.Record,
        settings: asyncpg.Record | None,
        alert: asyncpg.Record,
        pct: float,
    ) -> None:
        email_sent = False
        teams_sent = False
        slack_sent = False
        webhook_sent = False

        if settings and settings["alert_emails"]:
            email_sent = self.email.send_alert_email(
                list(settings["alert_emails"]),
                org["name"],
                alert["scope_value"] or "",
                pct,
                alert["message"],
            )
            if not email_sent:
                logger.warning(
                    "alert_email_not_sent",
                    org_id=str(org["id"]),
                    alert_id=str(alert["id"]),
                )

        async def _teams() -> bool:
            url = settings["teams_webhook_url"] if settings else None
            if not url:
                return False
            card = {
                "@type": "MessageCard",
                "summary": alert["message"],
                "text": alert["message"],
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.post(url, json=card)
                if resp.is_redirect:
                    raise RuntimeError("Teams webhook redirected")
                resp.raise_for_status()
            return True

        async def _slack() -> bool:
            url = settings["slack_webhook_url"] if settings else None
            if not url:
                return False
            body = {"text": alert["message"]}
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.post(url, json=body)
                if resp.is_redirect:
                    raise RuntimeError("Slack webhook redirected")
                resp.raise_for_status()
            return True

        async def _customer_webhooks() -> bool:
            rows = await db.fetch(
                """
                SELECT url, signing_secret_enc, events
                FROM outbound_webhooks
                WHERE org_id = $1 AND is_active = TRUE
                """,
                org["id"],
            )
            ok_any = False
            alert_payload = {
                "id": str(alert["id"]),
                "type": alert["type"],
                "message": alert["message"],
                "severity": alert["severity"],
                "threshold_percent": float(alert["threshold_percent"])
                if alert["threshold_percent"]
                else None,
            }
            for row in rows:
                events = row["events"] or []
                if "alert.fired" not in events:
                    continue
                secret = aes_decrypt(row["signing_secret_enc"])
                ok, _ = await self.webhooks.dispatch_alert_event(row["url"], secret, alert_payload, org["name"])
                ok_any = ok_any or ok
            return ok_any

        results = await asyncio.gather(_teams(), _slack(), _customer_webhooks(), return_exceptions=True)
        if len(results) >= 3:
            teams_sent = results[0] is True
            slack_sent = results[1] is True
            webhook_sent = results[2] is True

        await db.execute(
            """
            UPDATE alerts
            SET email_sent = $1, teams_sent = $2, slack_sent = $3, webhook_sent = $4
            WHERE id = $5
            """,
            email_sent,
            teams_sent,
            slack_sent,
            webhook_sent,
            alert["id"],
        )
        logger.info(
            "alert_fired",
            alert_id=str(alert["id"]),
            org_id=str(org["id"]),
            type=alert["type"],
            threshold=float(alert["threshold_percent"]) if alert["threshold_percent"] is not None else None,
            scope=alert["scope"],
            scope_value=alert["scope_value"],
            spend_pct=round(pct, 2),
            email_sent=email_sent,
            teams_sent=teams_sent,
            slack_sent=slack_sent,
            webhook_sent=webhook_sent,
        )
