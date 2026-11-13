"""HMAC validation for Teams/Slack incoming webhooks."""

import hashlib
import hmac
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request

from src.config.settings import get_settings
from src.utils.errors import AppError


def validate_hmac(provider: str) -> Callable[..., Any]:
    """Return a dependency that validates Teams or Slack request signatures."""

    async def _checker(request: Request) -> bytes:
        body = await request.body()
        settings = get_settings()

        if provider == "slack":
            secret = settings.slack_signing_secret
            if not secret:
                raise AppError("Slack signing secret not configured", status_code=500)
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            signature = request.headers.get("X-Slack-Signature", "")
            if abs(time.time() - int(timestamp or "0")) > 60 * 5:
                raise AppError("Stale Slack request", status_code=401)
            basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
            digest = "v0=" + hmac.new(
                secret.encode("utf-8"),
                basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(digest.encode(), signature.encode()):
                raise AppError("Invalid Slack signature", status_code=401)

        elif provider == "teams":
            secret = settings.teams_signing_secret
            if not secret:
                raise AppError("Teams signing secret not configured", status_code=500)
            signature = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(digest.encode(), signature.encode()):
                raise AppError("Invalid Teams signature", status_code=401)
        else:
            raise AppError(f"Unknown HMAC provider: {provider}", status_code=500)

        return body

    return _checker
