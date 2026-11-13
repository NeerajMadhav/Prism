"""OpenRouter LLM integration with Redis cache and budget tracking."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from src.config.redis_client import get_redis_client, redis_get, redis_set
from src.config.settings import get_settings
from src.utils.encrypt import aes_decrypt
from src.utils.logger import get_logger

logger = get_logger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMService:
    """Optional LLM helper; callers must handle None responses."""

    def __init__(
        self,
        org_id: UUID,
        api_key: str | None,
        model: str,
        monthly_budget_usd: float,
        is_enabled: bool,
    ) -> None:
        self.org_id = org_id
        self.api_key = api_key
        self.model = model
        self.monthly_budget_usd = monthly_budget_usd
        self.is_enabled = is_enabled

    @classmethod
    async def for_org(cls, conn: Any, org_id: UUID) -> LLMService | None:
        row = await conn.fetchrow("SELECT * FROM llm_configs WHERE org_id = $1", org_id)
        if row is None or not row["is_enabled"]:
            return None
        api_key = None
        if row["api_key_enc"]:
            api_key = aes_decrypt(row["api_key_enc"])
        return cls(
            org_id=org_id,
            api_key=api_key,
            model=row["model"],
            monthly_budget_usd=float(row["monthly_budget_usd"]),
            is_enabled=bool(row["is_enabled"]),
        )

    def can_call(self) -> bool:
        return bool(self.is_enabled and self.api_key)

    async def _spent_this_month(self) -> float:
        month = datetime.now(tz=UTC).strftime("%Y-%m")
        val = await redis_get(f"llm:monthly_spent:{self.org_id}:{month}")
        return float(val or 0)

    async def _incr_spend(self, amount: float) -> None:
        month = datetime.now(tz=UTC).strftime("%Y-%m")
        key = f"llm:monthly_spent:{self.org_id}:{month}"
        client = get_redis_client()
        if client is None:
            return
        try:
            await client.incrbyfloat(key, amount)
        except Exception as exc:
            logger.warning("llm_spend_track_failed", error=str(exc))

    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str | None:
        if not self.api_key:
            return None
        if await self._spent_this_month() >= self.monthly_budget_usd:
            return None
        prompt_hash = base64.urlsafe_b64encode(
            hashlib.sha256(f"{system}|{user}".encode()).digest()
        ).decode()
        cache_key = f"llm:{prompt_hash}"
        cached = await redis_get(cache_key)
        if cached:
            return cached

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system[:4000]},
                {"role": "user", "content": user[:4000]},
            ],
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": get_settings().frontend_url,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                usage = body.get("usage", {})
                cost_hint = float(usage.get("total_tokens", 0)) * 0.000002
                await self._incr_spend(cost_hint)
                await redis_set(cache_key, content, ex=86400)
                return content
        except Exception as exc:
            logger.warning(
                "llm_fallback",
                org_id=str(self.org_id),
                reason=str(exc)[:300],
            )
            return None

    async def explain_recommendation(self, title: str, description: str, savings: float) -> str | None:
        return await self.complete(
            "You are a FinOps assistant. Add a brief risk note to recommendations.",
            f"Title: {title}\nDescription: {description}\nSavings USD: {savings:.2f}",
            max_tokens=150,
        )

    async def answer_question(self, conn: Any, question: str) -> tuple[str | None, bool, int | None]:
        month_start = datetime.now(tz=UTC).replace(day=1).date()
        total = await conn.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0)
            FROM cost_records
            WHERE org_id = $1 AND time::date >= $2
            """,
            self.org_id,
            month_start,
        )
        context = f"Organization {self.org_id} month-to-date cloud spend: ${float(total or 0):.2f}."
        answer = await self.complete(
            "Answer FinOps questions using only the provided context.",
            f"Context:\n{context}\n\nQuestion: {question}",
            max_tokens=200,
        )
        return answer, answer is not None, None
