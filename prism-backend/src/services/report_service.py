"""Monthly report generation and delivery."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from src.services.email_service import EmailService
from src.services.llm_service import LLMService
from src.services.scorecard_service import ScorecardService
from src.utils.date_utils import current_month_start, next_month_start, utc_now
from src.utils.logger import get_logger

logger = get_logger(__name__)
email_service = EmailService()


class ReportService:
    """Build and send monthly FinOps reports."""

    @staticmethod
    async def generate(conn: Any, org_id: UUID, force: bool = False) -> bool:
        config = await conn.fetchrow("SELECT * FROM monthly_reports WHERE org_id = $1", org_id)
        if config is None:
            return False
        if not force and not config["is_active"]:
            return False

        org = await conn.fetchrow("SELECT name FROM organizations WHERE id = $1", org_id)
        org_name = org["name"] if org else "Organization"
        month_start = current_month_start()
        prev_start = (month_start.replace(day=1) - timedelta(days=1)).replace(day=1)

        current_total = await conn.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0)
            FROM cost_records WHERE org_id = $1 AND time::date >= $2
            """,
            org_id,
            month_start,
        )
        prev_total = await conn.fetchval(
            """
            SELECT COALESCE(SUM(cost_usd), 0)
            FROM cost_records
            WHERE org_id = $1 AND time::date >= $2 AND time::date < $3
            """,
            org_id,
            prev_start,
            month_start,
        )
        delta_pct = 0.0
        if prev_total and float(prev_total) > 0:
            delta_pct = (float(current_total) - float(prev_total)) / float(prev_total) * 100

        summary = (
            f"Total spend: ${float(current_total):.2f} "
            f"({'+' if delta_pct >= 0 else ''}{delta_pct:.1f}% vs last month)"
        )
        llm = await LLMService.for_org(conn, org_id)
        narrative = summary
        if llm and llm.can_call():
            enhanced = await llm.complete(
                "Write a one-paragraph executive summary for a monthly cloud cost report.",
                summary,
                max_tokens=400,
            )
            if enhanced:
                narrative = enhanced

        sections: list[str] = [
            f"<h1>{org_name} — Monthly Report {month_start.strftime('%B %Y')}</h1>",
            f"<p><strong>Executive summary:</strong> {narrative}</p>",
        ]

        by_provider = await conn.fetch(
            """
            SELECT provider, COALESCE(SUM(cost_usd), 0) AS total
            FROM cost_records
            WHERE org_id = $1 AND time::date >= $2
            GROUP BY provider ORDER BY total DESC
            """,
            org_id,
            month_start,
        )
        sections.append("<h2>Spend by platform</h2><ul>")
        for row in by_provider:
            sections.append(
                f"<li>{row['provider']}: ${float(row['total']):.2f}</li>"
            )
        sections.append("</ul>")

        if config["include_recommendations"]:
            recs = await conn.fetch(
                """
                SELECT title, savings_usd FROM recommendations
                WHERE org_id = $1 AND status = 'open'
                ORDER BY savings_usd DESC NULLS LAST
                LIMIT 5
                """,
                org_id,
            )
            if recs:
                sections.append("<h2>Top recommendations</h2><ul>")
                for rec in recs:
                    sections.append(
                        f"<li>{rec['title']} — ${float(rec['savings_usd'] or 0):.2f}</li>"
                    )
                sections.append("</ul>")

        if config["include_finops_scorecard"]:
            score = await ScorecardService.compute(conn, org_id, use_cache=False)
            sections.append(
                f"<h2>FinOps health</h2><p>Score: {score['overall_score']} ({score['grade']})</p>"
            )

        if config["include_commitments"]:
            commits = await conn.fetchval(
                """
                SELECT COUNT(*) FROM commitment_records
                WHERE org_id = $1 AND status = 'active'
                """,
                org_id,
            )
            sections.append(f"<h2>Commitments</h2><p>{commits} active commitments tracked.</p>")

        html = "\n".join(sections)
        text = narrative
        recipients = list(config["recipient_emails"] or [])
        if not recipients:
            logger.warning("report_no_recipients", org_id=str(org_id))
            return False

        subject = f"{org_name} — PRISM monthly report {month_start.strftime('%Y-%m')}"
        sent = email_service._send(recipients, subject, html, text)
        if not sent:
            logger.error(
                "report_send_failed",
                org_id=str(org_id),
                recipients=recipients,
            )
            return False
        next_send_day = int(config["send_day"] or 1)
        nxt = next_month_start()
        next_send = utc_now().replace(
            year=nxt.year,
            month=nxt.month,
            day=min(next_send_day, 28),
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        await conn.execute(
            """
            UPDATE monthly_reports
            SET last_sent = NOW(), next_send = $2
            WHERE org_id = $1
            """,
            org_id,
            next_send,
        )
        logger.info(
            "report_sent",
            org_id=str(org_id),
            recipients=recipients,
            month=month_start.isoformat(),
            spend_usd=float(current_total or 0),
        )
        return True
