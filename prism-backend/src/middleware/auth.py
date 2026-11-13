"""JWT / API-key authentication dependency."""

from datetime import UTC, datetime
from uuid import UUID

import asyncpg
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.database import get_db
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.logger import bind_user_context
from src.utils.security import decode_access_token, verify_password

_bearer = HTTPBearer(auto_error=False)


async def _resolve_api_key(token: str, db: asyncpg.Connection) -> UserContext:
    """Authenticate a prism_ API key against hashed rows."""
    prefix = token[6:14]
    rows = await db.fetch(
        """
        SELECT * FROM api_keys
        WHERE key_prefix = $1 AND revoked_at IS NULL
        """,
        prefix,
    )
    for row in rows:
        if verify_password(token, row["key_hash"]):
            if row["expires_at"] and row["expires_at"] < datetime.now(tz=UTC):
                raise AppError("API key expired", status_code=401, code="unauthorized")
            await db.execute("UPDATE api_keys SET last_used = NOW() WHERE id = $1", row["id"])
            bind_user_context(
                org_id=str(row["org_id"]),
                user_id=str(row["user_id"]),
                role="viewer",
            )
            return UserContext(
                user_id=row["user_id"],
                org_id=row["org_id"],
                role="viewer",
                email="api-key@prism.local",
                scopes=list(row["scopes"] or []),
                is_api_key=True,
            )
    raise AppError("Invalid API key", status_code=401, code="unauthorized")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    authorization: str | None = Header(default=None),
    db: asyncpg.Connection = Depends(get_db),
) -> UserContext:
    """Verify Bearer JWT or prism_ API key and return UserContext.

    JWT role/org are re-loaded from DB so demotion/removal take effect immediately
    (not only after access-token expiry).
    """
    token: str | None = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise AppError("Authentication required", status_code=401, code="unauthorized")

    if token.startswith("prism_"):
        return await _resolve_api_key(token, db)

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise AppError(str(exc), status_code=401, code="unauthorized") from exc

    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])
    membership = await db.fetchrow(
        """
        SELECT tm.role, u.email
        FROM team_members tm
        JOIN users u ON u.id = tm.user_id
        WHERE tm.user_id = $1 AND tm.org_id = $2 AND tm.invite_accepted = TRUE
        """,
        user_id,
        org_id,
    )
    if membership is None:
        raise AppError("Authentication required", status_code=401, code="unauthorized")

    bind_user_context(
        org_id=str(org_id),
        user_id=str(user_id),
        role=membership["role"],
    )
    return UserContext(
        user_id=user_id,
        org_id=org_id,
        role=membership["role"],
        email=membership["email"],
    )
