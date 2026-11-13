"""Spend forecast engine."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.utils.date_utils import current_month_start, days_elapsed_in_month, days_in_month, utc_now
from src.utils.logger import get_logger
from src.ws.ws_manager import worker_ws_broadcast

logger = get_logger(__name__)


class ForecastService:
    """Compute and persist org spend forecasts."""

    @staticmethod
    async def compute_for_org(conn: Any, org_id: UUID, provider: str | None = None) -> int:
        month_start = current_month_start()
        providers = (
            [provider]
            if provider
            else await conn.fetch(
                """
                SELECT DISTINCT provider FROM cloud_accounts
                WHERE org_id = $1 AND is_active = TRUE
                """,
                org_id,
            )
        )
        if provider is None:
            provider_rows = providers
            providers = [r["provider"] for r in provider_rows]

        updated = 0
        for prov in providers:
            daily_rows = await conn.fetch(
                """
                SELECT time::date AS day, COALESCE(SUM(cost_usd), 0) AS total
                FROM cost_records
                WHERE org_id = $1 AND provider = $2 AND time >= $3
                GROUP BY time::date
                ORDER BY day
                """,
                org_id,
                prov,
                month_start,
            )
            if not daily_rows:
                continue

            days_with_data = sum(1 for r in daily_rows if Decimal(r["total"]) > 0)
            elapsed = days_elapsed_in_month()
            total_spend = sum(Decimal(r["total"]) for r in daily_rows)
            daily_avg = total_spend / Decimal(elapsed) if elapsed > 0 else Decimal(0)

            last7 = daily_rows[-7:]
            if last7:
                rolling = sum(Decimal(r["total"]) for r in last7) / Decimal(len(last7))
                zero_in_last7 = any(Decimal(r["total"]) == 0 for r in last7)
                if zero_in_last7 and daily_avg > 0:
                    diff_pct = abs(rolling - daily_avg) / daily_avg * 100
                    if diff_pct > 20:
                        daily_avg = rolling

            data_coverage = "sufficient" if days_with_data >= 3 else "insufficient"
            projected = None
            will_breach = False
            if data_coverage == "sufficient":
                projected = float(daily_avg * days_in_month())
                cap_amount = await conn.fetchval(
                    """
                    SELECT cap_amount FROM budget_caps
                    WHERE org_id = $1 AND is_active = TRUE AND deleted_at IS NULL
                      AND scope = 'platform' AND scope_value = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    org_id,
                    prov,
                )
                if cap_amount:
                    will_breach = Decimal(projected) > Decimal(cap_amount)
                await conn.execute(
                    """
                    INSERT INTO spend_forecasts (
                      org_id, provider, forecast_month, daily_avg, projected_total,
                      cap_amount, will_breach, days_elapsed, days_with_data,
                      data_coverage, computed_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
                    ON CONFLICT (org_id, provider, forecast_month) DO UPDATE SET
                      daily_avg = EXCLUDED.daily_avg,
                      projected_total = EXCLUDED.projected_total,
                      cap_amount = EXCLUDED.cap_amount,
                      will_breach = EXCLUDED.will_breach,
                      days_elapsed = EXCLUDED.days_elapsed,
                      days_with_data = EXCLUDED.days_with_data,
                      data_coverage = EXCLUDED.data_coverage,
                      computed_at = NOW()
                    """,
                    org_id,
                    prov,
                    month_start,
                    float(daily_avg),
                    projected,
                    float(cap_amount) if cap_amount else None,
                    will_breach,
                    elapsed,
                    days_with_data,
                    data_coverage,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO spend_forecasts (
                      org_id, provider, forecast_month, daily_avg, projected_total,
                      will_breach, days_elapsed, days_with_data, data_coverage, computed_at
                    ) VALUES ($1,$2,$3,$4,NULL,FALSE,$5,$6,$7,NOW())
                    ON CONFLICT (org_id, provider, forecast_month) DO UPDATE SET
                      daily_avg = EXCLUDED.daily_avg,
                      projected_total = NULL,
                      data_coverage = EXCLUDED.data_coverage,
                      days_elapsed = EXCLUDED.days_elapsed,
                      days_with_data = EXCLUDED.days_with_data,
                      computed_at = NOW()
                    """,
                    org_id,
                    prov,
                    month_start,
                    float(daily_avg),
                    elapsed,
                    days_with_data,
                    data_coverage,
                )

            worker_ws_broadcast(
                str(org_id),
                "forecast.updated",
                {
                    "provider": prov,
                    "projected_total": projected,
                    "will_breach": will_breach,
                    "data_coverage": data_coverage,
                },
            )
            updated += 1
        return updated

    @staticmethod
    async def compute_forecast_accuracy(conn: Any, ref: date | None = None) -> int:
        today = ref or utc_now().date()
        if today.month == 1:
            last_month = date(today.year - 1, 12, 1)
        else:
            last_month = date(today.year, today.month - 1, 1)
        _, last_day = monthrange(last_month.year, last_month.month)
        month_end = date(last_month.year, last_month.month, last_day)

        rows = await conn.fetch(
            """
            SELECT id, org_id, provider, projected_total
            FROM spend_forecasts
            WHERE forecast_month = $1 AND actual_total IS NULL AND projected_total IS NOT NULL
            """,
            last_month,
        )
        updated = 0
        for row in rows:
            actual = await conn.fetchval(
                """
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM cost_records
                WHERE org_id = $1 AND provider = $2
                  AND time::date >= $3 AND time::date <= $4
                """,
                row["org_id"],
                row["provider"],
                last_month,
                month_end,
            )
            projected = Decimal(row["projected_total"] or 0)
            actual_d = Decimal(actual or 0)
            if actual_d > 0 and projected > 0:
                variance = float((actual_d - projected) / projected * 100)
            else:
                variance = None
            await conn.execute(
                """
                UPDATE spend_forecasts
                SET actual_total = $2, variance_pct = $3
                WHERE id = $1
                """,
                row["id"],
                float(actual_d),
                variance,
            )
            updated += 1
        return updated
