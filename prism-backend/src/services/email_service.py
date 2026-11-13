"""Transactional email via AWS SES (logs in development if SES not configured)."""

from typing import Any

import boto3

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    """Send transactional emails through SES."""

    def __init__(self) -> None:
        settings = get_settings()
        self.from_addr = settings.aws_ses_from
        self.frontend_url = settings.frontend_url
        self._client: Any = None
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self._client = boto3.client(
                "ses",
                region_name=settings.aws_ses_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )

    def _send(self, to: list[str], subject: str, html: str, text: str) -> bool:
        """Attempt send. Returns True only when SES accepted the message."""
        if not self._client:
            logger.info("email_skipped_no_ses", to=to, subject=subject)
            return False
        try:
            self._client.send_email(
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
            logger.info("email_sent", to=to, subject=subject)
            return True
        except Exception as exc:
            logger.error("email_failed", to=to, subject=subject, error=str(exc))
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
        subject = f"⚠️ {scope_value} at {pct:.0f}% — {org_name}"
        return self._send(emails, subject, f"<p>{message}</p>", message)

    def send_monthly_report(self, emails: list[str], org_name: str, html: str, text: str) -> bool:
        return self._send(emails, f"PRISM Monthly Report — {org_name}", html, text)

    def send_sync_failure(self, emails: list[str], org_name: str, account_name: str, error: str) -> bool:
        subject = f"Sync failed — {account_name} ({org_name})"
        return self._send(emails, subject, f"<p>{error}</p>", error)
