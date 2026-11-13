"""Org access dependency — path org_id must match JWT org_id."""

from typing import Any
from uuid import UUID

import asyncpg
from fastapi import Depends, Path

from src.config.database import get_db
from src.middleware.auth import get_current_user
from src.types.models import UserContext
from src.utils.errors import AppError


async def get_org_access(
    org_id: UUID = Path(..., alias="org_id"),
    current_user: UserContext = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Verify org scope and return organization row."""
    if current_user.org_id != org_id:
        # Same message as not found — no information leakage
        raise AppError("Organization not found", status_code=403, code="forbidden")

    org = await db.fetchrow("SELECT * FROM organizations WHERE id = $1", org_id)
    if org is None:
        raise AppError("Organization not found", status_code=403, code="forbidden")
    return dict(org)
