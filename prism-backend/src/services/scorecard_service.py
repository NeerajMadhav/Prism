"""FinOps health scorecard."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.config.redis_client import redis_get, redis_set
from src.utils.date_utils import current_month_start
from src.utils.logger import get_logger

logger = get_logger(__name__)

WEIGHTS = {
    "tagging_coverage": 20,
    "idle_resource_rate": 20,
    "commitment_coverage": 20,
    "budget_cap_coverage": 15,
    "forecast_accuracy": 10,
    "alert_response_time": 10,
    "recommendation_action_rate": 5,
}


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _status(score: float, green: float, yellow: float) -> str:
    if score >= green:
        return "green"
    if score >= yellow:
        return "yellow"
    return "red"


def _metric_score(value: float, green: float, yellow: float) -> float:
    if value >= green:
        return 100.0
    if value >= yellow:
        return 85.0
    if value > 0:
        return 60.0
    return 40.0


class ScorecardService:
    """Compute weighted FinOps health score."""

    @staticmethod
    async def compute(conn: Any, org_id: UUID, use_cache: bool = True) -> dict[str, Any]:
        cache_key = f"dash:{org_id}:scorecard"
        if use_cache:
            cached = await redis_get(cache_key)
            if cached:
                import json

                return json.loads(cached)

        month_start = current_month_start()
        tagged = await conn.fetchval(
            """
            SELECT COUNT(*) FROM cost_records
            WHERE org_id = $1 AND time::date >= $2
              AND tags <> '{}'::jsonb
              AND EXISTS (
                SELECT 1 FROM jsonb_each_text(tags) AS t(k, v)
                WHERE k NOT LIKE 'virtual\\_%'
              )
            """,
            org_id,
            month_start,
        )
        total_cost_rows = await conn.fetchval(
            """
            SELECT COUNT(*) FROM cost_records
            WHERE org_id = $1 AND time::date >= $2
            """,
            org_id,
            month_start,
        )
        tagging_pct = (int(tagged or 0) / int(total_cost_rows or 1)) * 100

        idle_count = await conn.fetchval(
            "SELECT COUNT(*) FROM resources WHERE org_id = $1 AND is_idle = TRUE",
            org_id,
        )
        total_resources = await conn.fetchval(
            "SELECT COUNT(*) FROM resources WHERE org_id = $1",
            org_id,
        )
        idle_rate = (1 - (int(idle_count or 0) / max(int(total_resources or 1), 1))) * 100

        avg_coverage = await conn.fetchval(
            """
            SELECT AVG(coverage_pct) FROM commitment_records
            WHERE org_id = $1 AND status = 'active'
            """,
            org_id,
        )
        commitment_cov = float(avg_coverage or 0)

        accounts = await conn.fetchval(
            "SELECT COUNT(*) FROM cloud_accounts WHERE org_id = $1 AND is_active = TRUE",
            org_id,
        )
        capped = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT scope_value) FROM budget_caps
            WHERE org_id = $1 AND is_active = TRUE AND deleted_at IS NULL
            """,
            org_id,
        )
        cap_cov = (int(capped or 0) / max(int(accounts or 1), 1)) * 100

        variance_rows = await conn.fetch(
            """
            SELECT variance_pct FROM spend_forecasts
            WHERE org_id = $1 AND variance_pct IS NOT NULL
            ORDER BY forecast_month DESC
            LIMIT 3
            """,
            org_id,
        )
        if variance_rows:
            avg_var = sum(abs(float(r["variance_pct"] or 0)) for r in variance_rows) / len(
                variance_rows
            )
            forecast_acc = max(0.0, 100.0 - avg_var)
        else:
            forecast_acc = 70.0

        response_hours = await conn.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (acknowledged_at - triggered_at)) / 3600.0)
            FROM alerts
            WHERE org_id = $1 AND acknowledged_at IS NOT NULL
            """,
            org_id,
        )
        if response_hours is None:
            alert_response = 100.0
        else:
            hrs = float(response_hours)
            alert_response = 100.0 if hrs < 4 else (85.0 if hrs <= 24 else 50.0)

        rec_total = await conn.fetchval(
            "SELECT COUNT(*) FROM recommendations WHERE org_id = $1",
            org_id,
        )
        rec_actioned = await conn.fetchval(
            """
            SELECT COUNT(*) FROM recommendations
            WHERE org_id = $1 AND status IN ('implemented', 'rejected', 'archived')
            """,
            org_id,
        )
        rec_rate = (int(rec_actioned or 0) / max(int(rec_total or 1), 1)) * 100

        metrics = [
            {
                "name": "tagging_coverage",
                "score": _metric_score(tagging_pct, 90, 70),
                "weight": WEIGHTS["tagging_coverage"],
                "current_value": round(tagging_pct, 2),
                "target_value": 90,
                "status": _status(tagging_pct, 90, 70),
            },
            {
                "name": "idle_resource_rate",
                "score": _metric_score(idle_rate, 95, 85),
                "weight": WEIGHTS["idle_resource_rate"],
                "current_value": round(idle_rate, 2),
                "target_value": 95,
                "status": _status(idle_rate, 95, 85),
            },
            {
                "name": "commitment_coverage",
                "score": _metric_score(commitment_cov, 80, 60),
                "weight": WEIGHTS["commitment_coverage"],
                "current_value": round(commitment_cov, 2),
                "target_value": 80,
                "status": _status(commitment_cov, 80, 60),
            },
            {
                "name": "budget_cap_coverage",
                "score": _metric_score(cap_cov, 100, 75),
                "weight": WEIGHTS["budget_cap_coverage"],
                "current_value": round(cap_cov, 2),
                "target_value": 100,
                "status": _status(cap_cov, 100, 75),
            },
            {
                "name": "forecast_accuracy",
                "score": _metric_score(forecast_acc, 90, 80),
                "weight": WEIGHTS["forecast_accuracy"],
                "current_value": round(forecast_acc, 2),
                "target_value": 90,
                "status": _status(forecast_acc, 90, 80),
            },
            {
                "name": "alert_response_time",
                "score": alert_response,
                "weight": WEIGHTS["alert_response_time"],
                "current_value": round(float(response_hours or 0), 2),
                "target_value": 4,
                "status": "green" if alert_response >= 85 else "yellow",
            },
            {
                "name": "recommendation_action_rate",
                "score": _metric_score(rec_rate, 80, 50),
                "weight": WEIGHTS["recommendation_action_rate"],
                "current_value": round(rec_rate, 2),
                "target_value": 80,
                "status": _status(rec_rate, 80, 50),
            },
        ]
        overall = sum(m["score"] * m["weight"] for m in metrics) / sum(WEIGHTS.values())
        result = {
            "overall_score": round(overall, 2),
            "grade": _grade(overall),
            "computed_at": month_start.isoformat(),
            "metrics": metrics,
        }
        import json

        await redis_set(cache_key, json.dumps(result), ex=3600)
        return result

    @staticmethod
    async def executive_view(conn: Any, org_id: UUID) -> dict[str, Any]:
        full = await ScorecardService.compute(conn, org_id)
        wins = [m["name"] for m in full["metrics"] if m["status"] == "green"][:3]
        risks = [m["name"] for m in full["metrics"] if m["status"] == "red"][:3]
        return {
            "overall_score": full["overall_score"],
            "grade": full["grade"],
            "top_wins": wins,
            "top_risks": risks,
        }
