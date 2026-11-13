"""Commitment sync and expiry tracking."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from src.services.connectors import get_connector
from src.services.fx_service import get_usd_rate
from src.utils.date_utils import utc_now
from src.utils.encrypt import aes_decrypt
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CommitmentService:
    """Sync commitment utilization from cloud connectors."""

    @staticmethod
    async def sync_for_org(conn: Any, org_id: UUID) -> int:
        accounts = await conn.fetch(
            """
            SELECT id, provider, credentials_enc, account_id
            FROM cloud_accounts
            WHERE org_id = $1 AND is_active = TRUE
            """,
            org_id,
        )
        upserted = 0
        org_row = await conn.fetchrow("SELECT currency FROM organizations WHERE id = $1", org_id)
        fx_rate = await get_usd_rate(org_row["currency"] if org_row else "USD")
        for account in accounts:
            try:
                creds_plain = aes_decrypt(account["credentials_enc"])
                connector = get_connector(
                    account["provider"],
                    creds_plain,
                    account["account_id"],
                    fx_rate=fx_rate,
                )
                commitments = await connector.get_commitments()
            except Exception as exc:
                logger.warning(
                    "commitment_sync_skipped",
                    org_id=str(org_id),
                    account_id=str(account["id"]),
                    error=str(exc),
                )
                continue
            for item in commitments:
                status = item.get("status", "active")
                end_date = item.get("end_date")
                if isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                today = utc_now().date()
                if end_date and end_date <= today + timedelta(days=30):
                    status = "expiring_soon"
                if end_date and end_date < today:
                    status = "expired"
                await conn.execute(
                    """
                    INSERT INTO commitment_records (
                      org_id, account_id, provider, commitment_type, resource_type,
                      arn_or_id, start_date, end_date, monthly_cost,
                      utilization_pct, coverage_pct, status, last_synced
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    org_id,
                    account["id"],
                    account["provider"],
                    item.get("commitment_type", "unknown"),
                    item.get("resource_type"),
                    item.get("arn_or_id"),
                    item.get("start_date"),
                    end_date,
                    item.get("monthly_cost"),
                    item.get("utilization_pct"),
                    item.get("coverage_pct"),
                    status,
                )
                upserted += 1
        return upserted
