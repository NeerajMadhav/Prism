"""GCP billing export connector via BigQuery.

Aligned with Google docs / FinOps practice:
- Aggregate by DATE(usage_start_time), not export_time
- Net cost = SUM(cost) + SUM(credits.amount)
- Filter on usage_start_time / DATE to limit scan cost
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from google.cloud import bigquery
from google.oauth2 import service_account

from src.types.models import ConnectorResult, HealthCheckResult
from src.utils.date_utils import to_utc_day
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GCPConnector:
    """Read cost from BigQuery billing export tables (one row per calendar day)."""

    def __init__(self, credentials: dict[str, Any], account_id: str) -> None:
        self.project_id = credentials["project_id"]
        self.dataset_id = credentials["dataset_id"]
        self.table_prefix = credentials["table_prefix"]
        self.service_account_info = credentials["service_account_json"]
        self.account_id = account_id
        creds = service_account.Credentials.from_service_account_info(self.service_account_info)
        self._client = bigquery.Client(project=self.project_id, credentials=creds)

    async def health_check(self) -> HealthCheckResult:
        try:
            self._client.get_dataset(self.dataset_id)
            return HealthCheckResult(ok=True)
        except Exception as exc:
            logger.warning("gcp_health_check_failed", account_id=self.account_id, error=str(exc))
            return HealthCheckResult(ok=False, error=str(exc))

    async def get_cost_and_usage(self, start_date: date, end_date: date) -> list[ConnectorResult]:
        table_ref = f"`{self.project_id}.{self.dataset_id}.{self.table_prefix}*`"
        # Net cost includes credits (promos, CUDs, sustained use) — matches Cloud Billing UI.
        query = f"""
            SELECT
                DATE(usage_start_time) AS usage_day,
                service.description AS service,
                IFNULL(location.region, '') AS region,
                SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) AS net_cost,
                ANY_VALUE(currency) AS currency
            FROM {table_ref}
            WHERE DATE(usage_start_time) >= @start_date
              AND DATE(usage_start_time) < @end_date
            GROUP BY usage_day, service, region
            HAVING net_cost != 0
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        )
        rows = self._client.query(query, job_config=job_config).result()
        results: list[ConnectorResult] = []
        today_utc = datetime.now(tz=UTC).date()
        for row in rows:
            cost_local = float(row.net_cost or 0)
            if cost_local == 0:
                continue
            # ponytail: multi-currency → treat as USD unless FX applied at sync; currency logged
            currency = str(getattr(row, "currency", None) or "USD").upper()
            if currency != "USD":
                logger.info(
                    "gcp_non_usd_cost",
                    account_id=self.account_id,
                    currency=currency,
                    day=str(row.usage_day),
                )
            usage_day = row.usage_day
            if isinstance(usage_day, datetime):
                usage_day = usage_day.date()
            is_estimate = usage_day >= today_utc
            results.append(
                ConnectorResult(
                    time=to_utc_day(usage_day),
                    service=str(row.service or "Unknown"),
                    region=str(row.region or ""),
                    cost_usd=cost_local,
                    cost_unblended_usd=cost_local,
                    cost_amortized_usd=cost_local,
                    tags={},
                    is_estimate=is_estimate,
                )
            )
        return results

    async def get_resources(self) -> list[dict[str, Any]]:
        return []

    async def get_commitments(self) -> list[dict[str, Any]]:
        return []
