"""Cost optimization recommendation engine."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.llm_service import LLMService
from src.utils.logger import get_logger
from src.ws.ws_manager import worker_ws_broadcast

logger = get_logger(__name__)


class RecommendationService:
    """Generate savings recommendations from idle and oversized resources."""

    @staticmethod
    async def generate_for_org(conn: Any, org_id: UUID) -> int:
        idle_rows = await conn.fetch(
            """
            SELECT id, name, provider, last_cost_usd, resource_type
            FROM resources
            WHERE org_id = $1 AND is_idle = TRUE
            ORDER BY last_cost_usd DESC NULLS LAST
            LIMIT 50
            """,
            org_id,
        )
        created = 0
        llm = await LLMService.for_org(conn, org_id)
        for row in idle_rows:
            exists = await conn.fetchval(
                """
                SELECT 1 FROM recommendations
                WHERE org_id = $1 AND resource_id = $2 AND status = 'open' AND type = 'idle_resource'
                """,
                org_id,
                row["id"],
            )
            if exists:
                continue
            savings = float(row["last_cost_usd"] or 0)
            title = f"Stop or resize idle {row['resource_type']}"
            description = f"Resource {row['name'] or row['id']} has been idle. Estimated monthly savings ${savings:.2f}."
            if llm and llm.can_call():
                enriched = await llm.explain_recommendation(title, description, savings)
                if enriched:
                    description = enriched
            await conn.execute(
                """
                INSERT INTO recommendations (
                  org_id, resource_id, type, title, description, savings_usd, confidence, status
                ) VALUES ($1,$2,'idle_resource',$3,$4,$5,'medium','open')
                """,
                org_id,
                row["id"],
                title,
                description,
                savings,
            )
            created += 1

        if created:
            top = await conn.fetchval(
                """
                SELECT COALESCE(MAX(savings_usd), 0)
                FROM recommendations
                WHERE org_id = $1 AND status = 'open'
                """,
                org_id,
            )
            worker_ws_broadcast(
                str(org_id),
                "recommendation.new",
                {"count": created, "top_savings": float(top or 0)},
            )
        return created
