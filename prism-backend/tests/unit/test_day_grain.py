"""Unit tests for UTC day normalization and Azure UsageDate / window helpers."""

import os
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://prism:prism@localhost:5432/prism")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("JWT_ACCESS_SECRET", "x" * 32)
os.environ.setdefault("JWT_REFRESH_SECRET", "y" * 32)
os.environ.setdefault(
    "ENCRYPTION_KEY",
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from src.services.connectors.azure import (  # noqa: E402
    AzureConnector,
    _azure_daily_windows,
    _parse_azure_usage_date,
)
from src.utils.date_utils import iter_days, to_utc_day  # noqa: E402


def test_to_utc_day_strips_time() -> None:
    ts = datetime(2026, 11, 13, 15, 45, 12, tzinfo=timezone.utc)
    day = to_utc_day(ts)
    assert day == datetime(2026, 11, 13, 0, 0, 0, tzinfo=timezone.utc)


def test_to_utc_day_from_date() -> None:
    assert to_utc_day(date(2026, 1, 2)) == datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)


def test_iter_days_exclusive_end() -> None:
    days = iter_days(date(2026, 11, 1), date(2026, 11, 4))
    assert days == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)]


def test_azure_usage_date_yyyymmdd() -> None:
    assert _parse_azure_usage_date(20261113) == date(2026, 11, 13)
    assert _parse_azure_usage_date("20261113") == date(2026, 11, 13)
    assert _parse_azure_usage_date("2026-11-13") == date(2026, 11, 13)


def test_azure_daily_windows_respect_31_day_cap() -> None:
    # 395-day backfill must chunk — Azure Daily max is 31 days.
    windows = _azure_daily_windows(date(2025, 1, 1), date(2025, 1, 1) + timedelta(days=395))
    assert len(windows) >= 13
    for start, end in windows:
        assert (end - start).days + 1 <= 31
    assert windows[0][0] == date(2025, 1, 1)
    assert windows[-1][1] == date(2025, 1, 1) + timedelta(days=394)


def test_azure_daily_windows_short_range() -> None:
    windows = _azure_daily_windows(date(2026, 11, 1), date(2026, 11, 10))
    assert windows == [(date(2026, 11, 1), date(2026, 11, 9))]


def test_azure_daily_windows_exact_31() -> None:
    windows = _azure_daily_windows(date(2026, 1, 1), date(2026, 2, 1))
    assert windows == [(date(2026, 1, 1), date(2026, 1, 31))]


def test_azure_parse_prefers_cost_falls_back_pretax() -> None:
    connector = AzureConnector.__new__(AzureConnector)
    connector.fx_rate = 1.0
    payload = {
        "properties": {
            "columns": [
                {"name": "PreTaxCost"},
                {"name": "UsageDate"},
                {"name": "ServiceName"},
                {"name": "ResourceLocation"},
            ],
            "rows": [[12.5, 20261110, "Virtual Machines", "eastus"]],
        }
    }
    rows = connector._parse_cost_rows(payload)
    assert len(rows) == 1
    assert rows[0].cost_usd == 12.5
    assert rows[0].service == "Virtual Machines"
    assert rows[0].time == datetime(2026, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
