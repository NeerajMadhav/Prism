"""Outbound webhook delivery with HMAC signing."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from src.utils.logger import get_logger
from src.utils.validate_webhook_url import verify_dispatch_url

logger = get_logger(__name__)


class OutboundWebhookService:
    """POST signed JSON payloads to customer webhook URLs."""

    def sign_payload(self, signing_secret: str, body: bytes) -> str:
        digest = hmac.new(signing_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    async def dispatch(
        self,
        url: str,
        signing_secret: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if not verify_dispatch_url(url):
            return False, "Webhook URL failed SSRF validation"
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        signature = self.sign_payload(signing_secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-PRISM-Signature": signature,
        }
        try:
            # follow_redirects=False: redirects can bypass DNS allowlist (SSRF).
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.post(url, content=body, headers=headers)
                if resp.is_redirect:
                    return False, "Webhook redirects are not allowed"
                resp.raise_for_status()
            return True, None
        except Exception as exc:
            logger.warning("webhook_dispatch_failed", url=url[:32], error=str(exc))
            return False, str(exc)

    async def dispatch_alert_event(
        self,
        url: str,
        signing_secret: str,
        alert: dict[str, Any],
        org_name: str,
    ) -> tuple[bool, str | None]:
        payload = {
            "event": "alert.fired",
            "org_name": org_name,
            "alert": alert,
        }
        return await self.dispatch(url, signing_secret, payload)

    async def send_test(
        self,
        url: str,
        signing_secret_enc: str,
        org_id: str,
    ) -> tuple[bool, int | None, str | None]:
        from src.utils.encrypt import aes_decrypt

        secret = aes_decrypt(signing_secret_enc)
        payload = {"event": "test", "org_id": org_id, "message": "PRISM webhook test"}
        if not verify_dispatch_url(url):
            return False, None, "Webhook URL failed SSRF validation"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = self.sign_payload(secret, body)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.post(
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-PRISM-Signature": signature,
                    },
                )
            if resp.is_redirect:
                return False, resp.status_code, "Webhook redirects are not allowed"
            return resp.status_code < 300, resp.status_code, None
        except Exception as exc:
            return False, None, str(exc)
