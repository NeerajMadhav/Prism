"""Celery task: sync cloud account cost and resource data."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from uuid import UUID

from src.services.connectors import get_connector, normalize_tags
from src.services.fx_service import get_usd_rate
from src.utils.cache import invalidate_dashboard_cache
from src.utils.date_utils import to_utc_day, utc_now
from src.utils.encrypt import aes_decrypt
from src.utils.logger import get_logger
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="prism-sync.sync_account", bind=True, max_retries=3)
def sync_account(self, account_id: str, org_id: str, backfill: bool = False) -> dict[str, object]:
    """Pull provider data for one cloud account."""
    return asyncio.run(
        _sync_account_async(UUID(account_id), UUID(org_id), backfill, delivery="celery")
    )


async def run_sync_inline(account_id: UUID, org_id: UUID, backfill: bool = False) -> dict[str, object]:
    """Run sync inside the API process (no Celery) with local WebSocket + alert delivery."""
    return await _sync_account_async(account_id, org_id, backfill, delivery="inline")


def schedule_sync_or_inline(
    *,
    account_id: UUID,
    org_id: UUID,
    backfill: bool,
) -> tuple[str, str]:
    """Queue via Celery when possible; otherwise start an in-process asyncio task.

    Returns (task_id, mode) where mode is 'queued' or 'inline'.
    """
    task_id = f"sync:{account_id}:{utc_now().date().isoformat()}:{'bf' if backfill else 'inc'}"
    try:
        result = sync_account.apply_async(
            args=[str(account_id), str(org_id), backfill],
            task_id=task_id,
            ignore_result=True,
        )
        return str(result.id), "queued"
    except Exception as exc:
        logger.warning(
            "sync_queue_unavailable_inline_fallback",
            account_id=str(account_id),
            org_id=str(org_id),
            error=str(exc),
        )

        async def _bg() -> None:
            try:
                await run_sync_inline(account_id, org_id, backfill)
            except Exception:
                logger.exception(
                    "inline_sync_failed",
                    account_id=str(account_id),
                    org_id=str(org_id),
                )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_bg())
        except RuntimeError:
            # No running loop (e.g. sync CLI) — run to completion.
            asyncio.run(run_sync_inline(account_id, org_id, backfill))
        return f"inline:{account_id}", "inline"


async def _sync_account_async(
    account_id: UUID,
    org_id: UUID,
    backfill: bool,
    *,
    delivery: str = "celery",
) -> dict[str, object]:
    from src.config.database import get_pool, init_db

    try:
        pool = get_pool()
    except RuntimeError:
        pool = await init_db()
    log_id: UUID | None = None
    async with pool.acquire() as db:
        account = await db.fetchrow(
            "SELECT * FROM cloud_accounts WHERE id = $1 AND org_id = $2",
            account_id,
            org_id,
        )
        if not account or not account["is_active"]:
            return {"status": "skipped"}

        log = await db.fetchrow(
            """
            INSERT INTO sync_logs (account_id, org_id, status)
            VALUES ($1, $2, 'running')
            RETURNING id
            """,
            account_id,
            org_id,
        )
        log_id = log["id"]
        await db.execute(
            "UPDATE cloud_accounts SET last_sync_status = 'running' WHERE id = $1",
            account_id,
        )

    try:
        async with pool.acquire() as db:
            account = await db.fetchrow("SELECT * FROM cloud_accounts WHERE id = $1", account_id)
            assert account is not None
            creds_plain = aes_decrypt(account["credentials_enc"])
            org_row = await db.fetchrow("SELECT currency FROM organizations WHERE id = $1", org_id)
            fx_rate = await get_usd_rate(org_row["currency"] if org_row else "USD")
            connector = get_connector(
                account["provider"],
                creds_plain,
                account["account_id"],
                fx_rate=fx_rate,
            )

            # UTC calendar days — same window basis for AWS, Azure, and GCP.
            end = utc_now().date()
            start = end - timedelta(days=395) if backfill else end - timedelta(days=3)
            sync_started_at = utc_now()
            logger.info(
                "sync_started",
                account_id=str(account_id),
                org_id=str(org_id),
                provider=account["provider"],
                backfill=backfill,
                start=start.isoformat(),
                end=end.isoformat(),
            )
            # end_exclusive = tomorrow so "today" is included for exclusive-end APIs.
            rows = await connector.get_cost_and_usage(start, end + timedelta(days=1))
            records = 0
            for row in rows:
                tags = normalize_tags(row.tags)
                day_ts = to_utc_day(row.time)
                await db.execute(
                    """
                    INSERT INTO cost_records (
                      org_id, account_id, provider, time, service, region,
                      cost_usd, cost_unblended_usd, cost_amortized_usd,
                      usage_quantity, usage_unit, tags, is_estimate
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13)
                    ON CONFLICT (account_id, time, service, region) DO UPDATE SET
                      cost_usd = EXCLUDED.cost_usd,
                      cost_unblended_usd = EXCLUDED.cost_unblended_usd,
                      cost_amortized_usd = EXCLUDED.cost_amortized_usd,
                      usage_quantity = EXCLUDED.usage_quantity,
                      usage_unit = EXCLUDED.usage_unit,
                      tags = cost_records.tags || EXCLUDED.tags,
                      is_estimate = EXCLUDED.is_estimate
                    """,
                    org_id,
                    account_id,
                    account["provider"],
                    day_ts,
                    row.service,
                    row.region,
                    row.cost_usd,
                    row.cost_unblended_usd,
                    row.cost_amortized_usd,
                    row.usage_quantity,
                    row.usage_unit,
                    json.dumps(tags),
                    row.is_estimate,
                )
                records += 1

            resources = await connector.get_resources()
            for res in resources:
                await db.execute(
                    """
                    INSERT INTO resources (
                      org_id, account_id, provider, resource_id, resource_type,
                      name, region, tags
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
                    ON CONFLICT (account_id, resource_id) DO UPDATE SET
                      name = EXCLUDED.name,
                      region = EXCLUDED.region,
                      tags = EXCLUDED.tags,
                      last_seen = CURRENT_DATE
                    """,
                    org_id,
                    account_id,
                    account["provider"],
                    res["resource_id"],
                    res["resource_type"],
                    res.get("name"),
                    res.get("region"),
                    json.dumps(res.get("tags", {})),
                )

            data_as_of = end if records else account["data_as_of"]
            await db.execute(
                """
                UPDATE cloud_accounts
                SET last_sync = $2, last_sync_status = 'success', last_sync_error = NULL,
                    last_sync_records = $3, data_as_of = $4
                WHERE id = $1
                """,
                account_id,
                utc_now(),
                records,
                data_as_of,
            )
            await db.execute(
                """
                UPDATE sync_logs
                SET status = 'success', finished_at = $2, records_synced = $3
                WHERE id = $1
                """,
                log_id,
                utc_now(),
                records,
            )

        await invalidate_dashboard_cache(str(org_id), account["provider"])
        from src.workers.alerts_worker import check_org_alerts
        from src.ws.ws_manager import _event_envelope, worker_ws_broadcast, ws_broadcast

        duration_ms = int((utc_now() - sync_started_at).total_seconds() * 1000)
        logger.info(
            "sync_completed",
            account_id=str(account_id),
            org_id=str(org_id),
            provider=account["provider"],
            records=records,
            duration_ms=duration_ms,
            data_as_of=str(data_as_of) if data_as_of else None,
            backfill=backfill,
            delivery=delivery,
        )
        event_data = {
            "provider": account["provider"],
            "account_id": str(account_id),
            "records": records,
        }
        if delivery == "inline":
            # Same API process — push WS locally; run alerts without Celery.
            await ws_broadcast(
                str(org_id),
                _event_envelope("sync.complete", str(org_id), event_data),
            )
            from src.services.alert_service import CapAlertService

            try:
                await CapAlertService().check_org(org_id)
            except Exception:
                logger.exception("inline_alert_check_failed", org_id=str(org_id))
        else:
            worker_ws_broadcast(str(org_id), "sync.complete", event_data)
            try:
                check_org_alerts.delay(str(org_id))
            except Exception as exc:
                logger.warning(
                    "alert_queue_unavailable",
                    org_id=str(org_id),
                    error=str(exc),
                )
                from src.services.alert_service import CapAlertService

                await CapAlertService().check_org(org_id)
        return {"status": "success", "records": records, "delivery": delivery}
    except Exception as exc:
        logger.exception(
            "sync_failed",
            account_id=str(account_id),
            org_id=str(org_id),
            error=str(exc)[:500],
        )
        async with pool.acquire() as db:
            await db.execute(
                """
                UPDATE cloud_accounts
                SET last_sync_status = 'failed', last_sync_error = $2
                WHERE id = $1
                """,
                account_id,
                str(exc)[:500],
            )
            if log_id:
                await db.execute(
                    """
                    UPDATE sync_logs
                    SET status = 'failed', finished_at = $2, error = $3
                    WHERE id = $1
                    """,
                    log_id,
                    utc_now(),
                    str(exc)[:500],
                )
        raise


@celery_app.task(name="prism-sync.schedule_daily")
def schedule_daily_sync() -> int:
    """Enqueue daily sync for all active accounts."""

    async def _run() -> int:
        from src.config.database import get_pool

        pool = get_pool()
        async with pool.acquire() as db:
            rows = await db.fetch(
                "SELECT id, org_id FROM cloud_accounts WHERE is_active = TRUE"
            )
        day = utc_now().date().isoformat()
        for row in rows:
            sync_account.apply_async(
                kwargs={
                    "account_id": str(row["id"]),
                    "org_id": str(row["org_id"]),
                    "backfill": False,
                },
                task_id=f"sync:{row['id']}:{day}:daily",
                ignore_result=True,
            )
        return len(rows)

    return asyncio.run(_run())


@celery_app.task(name="prism-sync.purge_old_data")
def purge_old_data() -> dict[str, int]:
    """Purge aged sync logs and acknowledged alerts."""

    async def _run() -> dict[str, int]:
        from src.config.database import get_pool

        pool = get_pool()
        async with pool.acquire() as db:
            sync_deleted = await db.fetchval(
                """
                WITH deleted AS (
                  DELETE FROM sync_logs WHERE started_at < NOW() - INTERVAL '90 days'
                  RETURNING id
                ) SELECT COUNT(*)::int FROM deleted
                """
            )
            alerts_deleted = await db.fetchval(
                """
                WITH deleted AS (
                  DELETE FROM alerts
                  WHERE triggered_at < NOW() - INTERVAL '180 days'
                    AND acknowledged_at IS NOT NULL
                  RETURNING id
                ) SELECT COUNT(*)::int FROM deleted
                """
            )
        return {
            "sync_logs": int(sync_deleted or 0),
            "alerts": int(alerts_deleted or 0),
        }

    return asyncio.run(_run())
