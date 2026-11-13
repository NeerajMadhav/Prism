"""LLM configuration and Q&A routes."""

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rate_limit import limiter
from src.middleware.rbac import require_role
from src.services.llm_service import LLMService
from src.types.models import UserContext
from src.utils.encrypt import aes_encrypt

router = APIRouter(prefix="/v1/orgs/{org_id}/llm", tags=["llm"])


class LLMConfigUpdate(BaseModel):
    api_key: str | None = None
    model: str | None = None
    monthly_budget_usd: float | None = None
    is_enabled: bool | None = None


class LLMQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.get("/")
async def get_llm_config(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow("SELECT model, monthly_budget_usd, is_enabled, api_key_enc FROM llm_configs WHERE org_id = $1", org["id"])
    if row is None:
        return {
            "model": "openai/gpt-4o-mini",
            "monthly_budget_usd": 20,
            "is_enabled": False,
            "api_key_set": False,
        }
    return {
        "model": row["model"],
        "monthly_budget_usd": float(row["monthly_budget_usd"]),
        "is_enabled": row["is_enabled"],
        "api_key_set": bool(row["api_key_enc"]),
    }


@router.put("/")
async def update_llm_config(
    body: LLMConfigUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    api_key_enc = None
    if body.api_key:
        api_key_enc = aes_encrypt(body.api_key)
    row = await db.fetchrow(
        """
        INSERT INTO llm_configs (org_id, api_key_enc, model, monthly_budget_usd, is_enabled)
        VALUES ($1, $2, COALESCE($3, 'openai/gpt-4o-mini'), COALESCE($4, 20), COALESCE($5, FALSE))
        ON CONFLICT (org_id) DO UPDATE SET
          api_key_enc = COALESCE($2, llm_configs.api_key_enc),
          model = COALESCE($3, llm_configs.model),
          monthly_budget_usd = COALESCE($4, llm_configs.monthly_budget_usd),
          is_enabled = COALESCE($5, llm_configs.is_enabled)
        RETURNING model, monthly_budget_usd, is_enabled, api_key_enc
        """,
        org["id"],
        api_key_enc,
        body.model,
        body.monthly_budget_usd,
        body.is_enabled,
    )
    return {
        "model": row["model"],
        "monthly_budget_usd": float(row["monthly_budget_usd"]),
        "is_enabled": row["is_enabled"],
        "api_key_set": bool(row["api_key_enc"]),
    }


@router.delete("/")
async def delete_llm_config(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute("DELETE FROM llm_configs WHERE org_id = $1", org["id"])
    return {"message": "LLM configuration removed"}


@router.post("/query")
@limiter.limit("20/hour")
async def llm_query(
    request: Request,
    body: LLMQueryRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    service = await LLMService.for_org(db, org["id"])
    if service is None or not service.can_call():
        return {
            "answer": None,
            "used_llm": False,
            "fallback_message": "LLM not configured.",
        }
    answer, used, tokens = await service.answer_question(db, body.question)
    return {"answer": answer, "used_llm": used, "tokens_used": tokens}
