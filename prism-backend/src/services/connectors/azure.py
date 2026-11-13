"""Azure Cost Management connector via httpx + azure-identity.

Aligned with Microsoft docs:
- Daily granularity max range = 31 days (chunk longer windows)
- timePeriod from/to are inclusive (use 00:00:00Z .. 23:59:59Z)
- Follow properties.nextLink for pagination (max ~5000 rows/page)
- UsageDate is YYYYMMDD number
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from azure.identity import ClientSecretCredential

from src.services.connectors.tags import normalize_tags
from src.types.models import ConnectorResult, HealthCheckResult
from src.utils.date_utils import to_utc_day
from src.utils.logger import get_logger
from src.utils.retry import with_retry

logger = get_logger(__name__)

COST_API_VERSION = "2023-11-01"
SUBSCRIPTION_API_VERSION = "2020-01-01"
# https://learn.microsoft.com — Daily granularity max 31 days
_AZURE_DAILY_MAX_DAYS = 31


def _parse_azure_usage_date(raw: Any) -> date | None:
    """Parse Azure UsageDate (YYYY-MM-DD or YYYYMMDD int/string) to a calendar date."""
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, (int, float)):
        s = f"{int(raw):08d}"
    else:
        s = str(raw).strip()
    if not s:
        return None
    if s.isdigit() and len(s) == 8:
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    return date.fromisoformat(s[:10])


def _azure_daily_windows(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    """Split [start, end_exclusive) into inclusive windows of at most 31 days."""
    if end_exclusive <= start:
        return []
    windows: list[tuple[date, date]] = []
    cur = start
    last = end_exclusive - timedelta(days=1)
    while cur <= last:
        chunk_end = min(cur + timedelta(days=_AZURE_DAILY_MAX_DAYS - 1), last)
        windows.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return windows


class AzureConnector:
    """Query Azure Cost Management for daily spend."""

    def __init__(self, credentials: dict[str, Any], account_id: str, fx_rate: float) -> None:
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.subscription_id = credentials["subscription_id"]
        self.account_id = account_id
        self.fx_rate = fx_rate
        self._credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

    def _token(self) -> str:
        scope = "https://management.azure.com/.default"
        return self._credential.get_token(scope).token

    async def health_check(self) -> HealthCheckResult:
        try:
            await with_retry(self._health_check_request)
            return HealthCheckResult(ok=True)
        except Exception as exc:
            logger.warning("azure_health_check_failed", account_id=self.account_id, error=str(exc))
            return HealthCheckResult(ok=False, error=str(exc))

    async def _health_check_request(self) -> None:
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"?api-version={SUBSCRIPTION_API_VERSION}"
        )
        headers = {"Authorization": f"Bearer {self._token()}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

    async def get_cost_and_usage(self, start_date: date, end_date: date) -> list[ConnectorResult]:
        """Fetch daily ActualCost for [start_date, end_date) exclusive end (AWS-compatible)."""
        results: list[ConnectorResult] = []
        for win_start, win_end in _azure_daily_windows(start_date, end_date):
            chunk = await with_retry(lambda s=win_start, e=win_end: self._query_window(s, e))
            results.extend(chunk)
        return results

    async def _query_window(self, from_day: date, to_day: date) -> list[ConnectorResult]:
        body = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "timePeriod": {
                "from": f"{from_day.isoformat()}T00:00:00Z",
                "to": f"{to_day.isoformat()}T23:59:59Z",
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [
                    {"type": "Dimension", "name": "ServiceName"},
                    {"type": "Dimension", "name": "ResourceLocation"},
                ],
            },
        }
        url: str | None = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/providers/Microsoft.CostManagement/query?api-version={COST_API_VERSION}"
        )
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }
        out: list[ConnectorResult] = []
        seen_cursors: set[str] = set()
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            first = True
            while url:
                if first:
                    resp = await client.post(url, headers=headers, json=body)
                    first = False
                else:
                    # nextLink is a full URL — GET continuation (no body)
                    resp = await client.get(url, headers={"Authorization": headers["Authorization"]})
                resp.raise_for_status()
                payload = resp.json()
                out.extend(self._parse_cost_rows(payload))
                next_link = payload.get("properties", {}).get("nextLink") or None
                if next_link and next_link in seen_cursors:
                    logger.warning(
                        "azure_nextlink_cycle",
                        account_id=self.account_id,
                        cursor=next_link[:120],
                    )
                    break
                if next_link:
                    seen_cursors.add(next_link)
                url = next_link
        return out

    def _parse_cost_rows(self, payload: dict[str, Any]) -> list[ConnectorResult]:
        props = payload.get("properties", {})
        columns = [c.get("name") for c in props.get("columns", [])]
        rows = props.get("rows", [])
        results: list[ConnectorResult] = []
        today_utc = datetime.now(tz=UTC).date()
        for row in rows:
            data = dict(zip(columns, row, strict=False))
            # Prefer Cost; fall back to PreTaxCost (common in some scopes)
            cost_local = float(data.get("Cost") or data.get("PreTaxCost") or 0)
            if cost_local <= 0:
                continue
            cost_usd = cost_local * self.fx_rate
            day = _parse_azure_usage_date(data.get("UsageDate") or data.get("Date"))
            if day is None:
                continue
            service = str(data.get("ServiceName") or "Unknown")
            region = str(
                data.get("ResourceLocation")
                or data.get("ResourceGroupName")
                or data.get("ResourceGroup")
                or ""
            )
            tags = normalize_tags(data.get("Tags") if isinstance(data.get("Tags"), dict) else {})
            is_estimate = day >= today_utc
            results.append(
                ConnectorResult(
                    time=to_utc_day(day),
                    service=service,
                    region=region,
                    cost_usd=cost_usd,
                    cost_unblended_usd=cost_usd,
                    cost_amortized_usd=cost_usd,
                    tags=tags,
                    is_estimate=is_estimate,
                )
            )
        return results

    async def get_resources(self) -> list[dict[str, Any]]:
        # ponytail: full ARM inventory is heavy; cost-derived names suffice for v1
        return []

    async def get_commitments(self) -> list[dict[str, Any]]:
        return []
