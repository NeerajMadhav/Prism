"""FinOps health scorecard routes."""

import asyncpg
from fastapi import APIRouter, Depends

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.services.scorecard_service import ScorecardService
from src.types.models import UserContext

router = APIRouter(prefix="/v1/orgs/{org_id}/scorecard", tags=["scorecard"])


@router.get("/")
async def get_scorecard(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    from uuid import UUID

    return await ScorecardService.compute(db, UUID(str(org["id"])))


@router.get("/executive")
async def get_executive_scorecard(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    from uuid import UUID

    return await ScorecardService.executive_view(db, UUID(str(org["id"])))
