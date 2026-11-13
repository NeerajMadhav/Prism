"""Role-based access control and API-key scope enforcement."""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request

from src.middleware.auth import get_current_user
from src.types.models import ROLE_RANK, UserContext
from src.utils.errors import AppError

# API keys may only call routes that map to an explicit scope they hold.
_SCOPE_PATH_MARKERS: tuple[tuple[str, str], ...] = (
    ("/costs", "cost.read"),
    ("/alerts", "alerts.read"),
    ("/reports", "reports.read"),
    ("/webhooks", "webhooks.write"),
)


def required_api_scope(path: str) -> str | None:
    """Return the scope required for an API-key call to this path, if any."""
    for marker, scope in _SCOPE_PATH_MARKERS:
        if marker in path:
            return scope
    return None


def require_role(min_role: str) -> Callable[..., Any]:
    """Return a dependency that enforces minimum role rank (and API-key scopes)."""

    async def _checker(
        request: Request,
        current_user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if current_user.is_api_key:
            scope = required_api_scope(request.url.path)
            if scope is None or scope not in current_user.scopes:
                raise AppError(
                    "API key missing required scope",
                    status_code=403,
                    code="forbidden",
                )

        user_rank = ROLE_RANK.get(current_user.role, 0)
        required = ROLE_RANK.get(min_role, 99)
        if user_rank < required:
            raise AppError("Insufficient permissions", status_code=403, code="forbidden")
        return current_user

    return _checker
