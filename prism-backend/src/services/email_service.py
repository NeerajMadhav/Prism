"""Transactional email via Microsoft Graph (preferred) or AWS SES fallback."""

from __future__ import annotations

import base64
from typing import Any

import boto3
import httpx

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    """Send transactional emails through Graph when configured, else SES."""

    def __init__(self) -> None:
        settings = get_settings()
        self.from_addr = settings.aws_ses_from
        self.frontend_url = settings.frontend_url
        self._ses: Any = None
        self._graph = {
            "tenant": settings.ms_graph_tenant_id.strip(),
            "client_id": settings.ms_graph_client_id.strip(),
            "client_secret": settings.ms_graph_client_secret.strip(),
            "sender": settings.ms_graph_sender.strip(),
        }
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self._ses = boto3.client(
                "ses",
                region_name=settings.aws_ses_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )

    @property
    def graph_configured(self) -> bool:
        g = self._graph
        return bool(g["tenant"] and g["client_id"] and g["client_secret"] and g["sender"])

    def _graph_token(self) -> str | None:
        if not self.graph_configured:
            return None
        url = f"https://login.microsoftonline.com/{self._graph['tenant']}/oauth2/v2.0/token"
        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(
                    url,
                    data={
                        "client_id": self._graph["client_id"],
                        "client_secret": self._graph["client_secret"],
                        "scope": "https://graph.microsoft.com/.default",
                        "grant_type": "client_credentials",
                    },
                )
                res.raise_for_status()
                return str(res.json()["access_token"])
        except Exception as exc:
            logger.error("ms_graph_token_failed", error=str(exc))
            return None

    def _send_graph(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        token = self._graph_token()
        if not token:
            return False
        sender = self._graph["sender"]
        message: dict[str, Any] = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html or text},
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        }
        if attachments:
            message["attachments"] = attachments
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(
                    f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"message": message, "saveToSentItems": True},
                )
                res.raise_for_status()
            logger.info("email_sent", transport="ms_graph", to=to, subject=subject)
            return True
        except Exception as exc:
            logger.error("ms_graph_send_failed", to=to, subject=subject, error=str(exc))
            return False

    def _send_ses(self, to: list[str], subject: str, html: str, text: str) -> bool:
        if not self._ses:
            return False
        try:
            self._ses.send_email(
                Source=self.from_addr,
                Destination={"ToAddresses": to},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Html": {"Data": html},
                        "Text": {"Data": text},
                    },
                },
            )
            logger.info("email_sent", transport="ses", to=to, subject=subject)
            return True
        except Exception as exc:
            logger.error("email_failed", transport="ses", to=to, subject=subject, error=str(exc))
            return False

    def _send(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str,
        pdf_bytes: bytes | None = None,
        pdf_filename: str = "prism-report.pdf",
    ) -> bool:
        """Send via Graph when configured; otherwise SES; otherwise log skip."""
        attachments: list[dict[str, Any]] | None = None
        if pdf_bytes:
            attachments = [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": pdf_filename,
                    "contentType": "application/pdf",
                    "contentBytes": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            ]
        if self.graph_configured:
            if self._send_graph(to, subject, html, text, attachments=attachments):
                return True
            logger.warning("ms_graph_send_fallback_ses", subject=subject)
        if self._send_ses(to, subject, html, text):
            return True
        logger.info("email_skipped_no_transport", to=to, subject=subject)
        return False

    def send_verification(self, email: str, user_id: str, token: str) -> bool:
        link = f"{self.frontend_url}/verify-email?userId={user_id}&token={token}"
        return self._send(
            [email],
            "Verify your PRISM account",
            f"<p>Click to verify: <a href='{link}'>{link}</a></p>",
            f"Verify your account: {link}",
        )

    def send_password_reset(self, email: str, user_id: str, token: str) -> bool:
        link = f"{self.frontend_url}/reset-password?userId={user_id}&token={token}"
        return self._send(
            [email],
            "Reset your PRISM password",
            f"<p>Reset password: <a href='{link}'>{link}</a></p>",
            f"Reset password: {link}",
        )

    def send_invite(self, email: str, org_id: str, org_name: str, token: str, role: str) -> bool:
        link = f"{self.frontend_url}/accept-invite?token={token}&org_id={org_id}"
        return self._send(
            [email],
            f"You're invited to {org_name} on PRISM",
            f"<p>Join as {role}: <a href='{link}'>{link}</a></p>",
            f"Join {org_name} as {role}: {link}",
        )

    def send_alert_email(
        self,
        emails: list[str],
        org_name: str,
        scope_value: str,
        pct: float,
        message: str,
    ) -> bool:
        subject = f"{scope_value} at {pct:.0f}% — {org_name}"
        return self._send(emails, subject, f"<p>{message}</p>", message)

    def send_monthly_report(
        self,
        emails: list[str],
        org_name: str,
        html: str,
        text: str,
        pdf_bytes: bytes | None = None,
    ) -> bool:
        return self._send(
            emails,
            f"PRISM Monthly Report — {org_name}",
            html,
            text,
            pdf_bytes=pdf_bytes,
            pdf_filename=f"prism-report-{org_name.replace(' ', '-').lower()}.pdf",
        )

    def send_sync_failure(
        self, emails: list[str], org_name: str, account_name: str, error: str
    ) -> bool:
        subject = f"Sync failed — {account_name} ({org_name})"
        return self._send(emails, subject, f"<p>{error}</p>", error)
