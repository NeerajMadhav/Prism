"""Monthly report generation, HTML preview, PDF, and delivery."""

from __future__ import annotations

from datetime import timedelta
from html import escape
from typing import Any
from uuid import UUID

from src.services.email_service import EmailService
from src.services.llm_service import LLMService
from src.services.pdf_service import html_to_pdf
from src.services.scorecard_service import ScorecardService
from src.utils.date_utils import current_month_start, next_month_start, utc_now
from src.utils.logger import get_logger

logger = get_logger(__name__)
email_service = EmailService()


def _money(value: Any) -> str:
    return f"${float(value or 0):,.2f}"


class ReportService:
    """Build and send monthly FinOps reports."""

    @staticmethod
    async def build_html(conn: Any, org_id: UUID) -> dict[str, Any]:
        """Return professional HTML + plain text for the current month."""
        config = await conn.fetchrow("SELECT * FROM monthly_reports WHERE org_id = $1", org_id)
        org = await conn.fetchrow("SELECT name, currency FROM organizations WHERE id = $1", org_id)
        org_name = org["name"] if org else "Organization"
        month_start = current_month_start()
        prev_start = (month_start.replace(day=1) - timedelta(days=1)).replace(day=1)
        month_label = month_start.strftime("%B %Y")

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
        delta_label = f"{'+' if delta_pct >= 0 else ''}{delta_pct:.1f}% vs prior month"

        summary = (
            f"Total spend: {_money(current_total)} ({delta_label})"
        )
        narrative = summary
        llm = await LLMService.for_org(conn, org_id)
        if llm and llm.can_call():
            enhanced = await llm.complete(
                "Write a clear one-paragraph executive summary for a monthly cloud cost report.",
                summary,
                max_tokens=400,
            )
            if enhanced:
                narrative = enhanced

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
        by_account = await conn.fetch(
            """
            SELECT ca.display_name, ca.provider, ca.account_id,
                   COALESCE(SUM(cr.cost_usd), 0) AS total
            FROM cloud_accounts ca
            LEFT JOIN cost_records cr
              ON cr.account_id = ca.id AND cr.org_id = ca.org_id AND cr.time::date >= $2
            WHERE ca.org_id = $1 AND ca.is_active = TRUE
            GROUP BY ca.id, ca.display_name, ca.provider, ca.account_id
            ORDER BY total DESC
            """,
            org_id,
            month_start,
        )

        include_recs = True if config is None else bool(config["include_recommendations"])
        include_score = True if config is None else bool(config["include_finops_scorecard"])
        include_commits = True if config is None else bool(config["include_commitments"])

        recs: list[Any] = []
        if include_recs:
            recs = await conn.fetch(
                """
                SELECT title, savings_usd FROM recommendations
                WHERE org_id = $1 AND status = 'open'
                ORDER BY savings_usd DESC NULLS LAST
                LIMIT 5
                """,
                org_id,
            )

        score_html = ""
        if include_score:
            score = await ScorecardService.compute(conn, org_id, use_cache=False)
            score_html = (
                f"<tr><td>FinOps score</td><td><strong>{escape(str(score['overall_score']))}</strong> "
                f"({escape(str(score['grade']))})</td></tr>"
            )

        commits_html = ""
        if include_commits:
            commits = await conn.fetchval(
                """
                SELECT COUNT(*) FROM commitment_records
                WHERE org_id = $1 AND status = 'active'
                """,
                org_id,
            )
            commits_html = (
                f"<tr><td>Active commitments</td><td>{int(commits or 0)}</td></tr>"
            )

        provider_rows = "".join(
            f"<tr><td>{escape(str(r['provider']).upper())}</td>"
            f"<td class='num'>{_money(r['total'])}</td></tr>"
            for r in by_provider
        ) or "<tr><td colspan='2'>No spend recorded this month.</td></tr>"

        account_rows = "".join(
            f"<tr><td>{escape(r['display_name'])}</td>"
            f"<td>{escape(str(r['provider']).upper())}</td>"
            f"<td><code>{escape(r['account_id'])}</code></td>"
            f"<td class='num'>{_money(r['total'])}</td></tr>"
            for r in by_account
        ) or "<tr><td colspan='4'>No accounts connected.</td></tr>"

        rec_rows = "".join(
            f"<tr><td>{escape(r['title'])}</td>"
            f"<td class='num'>{_money(r['savings_usd'])}</td></tr>"
            for r in recs
        ) or "<tr><td colspan='2'>No open recommendations.</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>PRISM Monthly Report — {escape(org_name)} — {month_label}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; color: #111827; margin: 0; padding: 32px; background: #fff; }}
    h1 {{ font-size: 22px; margin: 0 0 4px; }}
    h2 {{ font-size: 16px; margin: 28px 0 10px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }}
    .muted {{ color: #6b7280; font-size: 13px; }}
    .card {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px 18px; margin: 16px 0; }}
    .kpi {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ text-align: left; padding: 8px 6px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
    th {{ color: #6b7280; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    code {{ font-family: ui-monospace, Consolas, monospace; font-size: 11px; }}
    .footer {{ margin-top: 36px; font-size: 11px; color: #9ca3af; }}
  </style>
</head>
<body>
  <p class="muted">PRISM FinOps</p>
  <h1>{escape(org_name)} — Monthly cloud cost report</h1>
  <p class="muted">{month_label} · Generated {escape(utc_now().strftime('%Y-%m-%d %H:%M UTC'))}</p>

  <div class="card">
    <div class="muted">Month-to-date spend</div>
    <div class="kpi">{_money(current_total)}</div>
    <div class="muted">{escape(delta_label)} · Prior month {_money(prev_total)}</div>
  </div>

  <h2>Executive summary</h2>
  <p>{escape(narrative)}</p>

  <h2>Spend by cloud provider</h2>
  <table>
    <thead><tr><th>Provider</th><th class="num">Spend (USD)</th></tr></thead>
    <tbody>{provider_rows}</tbody>
  </table>

  <h2>Spend by account</h2>
  <p class="muted">Multiple accounts of the same provider appear as separate rows.</p>
  <table>
    <thead>
      <tr><th>Account</th><th>Provider</th><th>Cloud ID</th><th class="num">Spend (USD)</th></tr>
    </thead>
    <tbody>{account_rows}</tbody>
  </table>

  <h2>Top savings recommendations</h2>
  <table>
    <thead><tr><th>Recommendation</th><th class="num">Est. savings</th></tr></thead>
    <tbody>{rec_rows}</tbody>
  </table>

  <h2>Health snapshot</h2>
  <table>
    <tbody>
      {score_html}
      {commits_html}
      <tr><td>Connected accounts</td><td>{len(by_account)}</td></tr>
    </tbody>
  </table>

  <p class="footer">Confidential — for {escape(org_name)} stakeholders. Generated by PRISM.</p>
</body>
</html>"""

        text = (
            f"{org_name} — Monthly report {month_label}\n"
            f"{summary}\n\n{narrative}\n"
        )
        return {
            "html": html,
            "text": text,
            "month": month_start.isoformat(),
            "month_label": month_label,
            "org_name": org_name,
            "total_usd": float(current_total or 0),
        }

    @staticmethod
    async def generate(conn: Any, org_id: UUID, force: bool = False) -> bool:
        config = await conn.fetchrow("SELECT * FROM monthly_reports WHERE org_id = $1", org_id)
        if config is None:
            return False
        if not force and not config["is_active"]:
            return False

        built = await ReportService.build_html(conn, org_id)
        recipients = list(config["recipient_emails"] or [])
        if not recipients:
            logger.warning("report_no_recipients", org_id=str(org_id))
            return False

        pdf_bytes: bytes | None = None
        try:
            pdf_bytes = html_to_pdf(built["html"])
        except Exception as exc:
            logger.warning("report_pdf_skipped", org_id=str(org_id), error=str(exc))

        sent = email_service.send_monthly_report(
            recipients,
            built["org_name"],
            built["html"],
            built["text"],
            pdf_bytes=pdf_bytes,
        )
        if not sent:
            logger.error("report_send_failed", org_id=str(org_id), recipients=recipients)
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
            month=built["month"],
            spend_usd=built["total_usd"],
        )
        return True
