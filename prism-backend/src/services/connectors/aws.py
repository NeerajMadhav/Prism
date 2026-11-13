"""AWS cost and resource connector via boto3."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import boto3

from src.services.connectors.tags import normalize_tags
from src.types.models import ConnectorResult, HealthCheckResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AWSConnector:
    """STS assume-role then Cost Explorer + EC2 discovery."""

    def __init__(self, credentials: dict[str, Any], account_id: str) -> None:
        self.role_arn = credentials["role_arn"]
        self.external_id = credentials["external_id"]
        self.region = credentials.get("region", "us-east-1")
        self.account_id = account_id
        self._session: dict[str, str] | None = None

    def _assume_role(self) -> dict[str, str]:
        if self._session:
            return self._session
        sts = boto3.client("sts", region_name=self.region)
        resp = sts.assume_role(
            RoleArn=self.role_arn,
            RoleSessionName="prism",
            ExternalId=self.external_id,
        )
        creds = resp["Credentials"]
        self._session = {
            "aws_access_key_id": creds["AccessKeyId"],
            "aws_secret_access_key": creds["SecretAccessKey"],
            "aws_session_token": creds["SessionToken"],
        }
        return self._session

    def _client(self, service: str, region: str | None = None) -> Any:
        session_creds = self._assume_role()
        return boto3.client(
            service,
            region_name=region or self.region,
            **session_creds,
        )

    async def health_check(self) -> HealthCheckResult:
        try:
            await asyncio.to_thread(self._health_check_sync)
            return HealthCheckResult(ok=True)
        except Exception as exc:
            logger.warning("aws_health_check_failed", account_id=self.account_id, error=str(exc))
            return HealthCheckResult(ok=False, error=str(exc))

    def _health_check_sync(self) -> None:
        ce = self._client("ce", "us-east-1")
        end = datetime.now(tz=UTC).date()
        start = end - timedelta(days=1)
        ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["NetUnblendedCost"],
        )

    async def get_cost_and_usage(self, start_date: date, end_date: date) -> list[ConnectorResult]:
        return await asyncio.to_thread(self._get_cost_and_usage_sync, start_date, end_date)

    def _get_cost_and_usage_sync(self, start_date: date, end_date: date) -> list[ConnectorResult]:
        ce = self._client("ce", "us-east-1")
        results: list[ConnectorResult] = []
        token: str | None = None
        while True:
            # Net* metrics include discounts; exclude Credit/Refund RECORD_TYPE
            # (AWS CE / FinOps best practice for operational spend views).
            params: dict[str, Any] = {
                "TimePeriod": {"Start": start_date.isoformat(), "End": end_date.isoformat()},
                "Granularity": "DAILY",
                "Metrics": ["NetUnblendedCost", "NetAmortizedCost", "UsageQuantity"],
                "GroupBy": [
                    {"Type": "DIMENSION", "Key": "SERVICE"},
                    {"Type": "DIMENSION", "Key": "REGION"},
                ],
                "Filter": {
                    "Not": {
                        "Dimensions": {
                            "Key": "RECORD_TYPE",
                            "Values": ["Credit", "Refund"],
                        }
                    }
                },
            }
            if token:
                params["NextPageToken"] = token
            resp = ce.get_cost_and_usage(**params)
            for row in resp.get("ResultsByTime", []):
                # AWS CE DAILY Start is the calendar day; Estimated marks incomplete days.
                day = datetime.fromisoformat(row["TimePeriod"]["Start"]).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC
                )
                is_estimate = bool(row.get("Estimated", False))
                for group in row.get("Groups", []):
                    keys = group.get("Keys", ["", ""])
                    service = keys[0] if keys else "Unknown"
                    region = keys[1] if len(keys) > 1 else ""
                    metrics = group.get("Metrics", {})
                    unblended = float(metrics.get("NetUnblendedCost", {}).get("Amount", 0) or 0)
                    amortized = float(metrics.get("NetAmortizedCost", {}).get("Amount", 0) or 0)
                    if unblended == 0 and amortized == 0:
                        continue
                    usage_qty_raw = metrics.get("UsageQuantity", {}).get("Amount")
                    usage_qty = float(usage_qty_raw) if usage_qty_raw else None
                    usage_unit = metrics.get("UsageQuantity", {}).get("Unit")
                    results.append(
                        ConnectorResult(
                            time=day,
                            service=service,
                            region=region,
                            cost_usd=unblended,
                            cost_unblended_usd=unblended,
                            cost_amortized_usd=amortized,
                            usage_quantity=usage_qty,
                            usage_unit=usage_unit,
                            tags={},
                            is_estimate=is_estimate,
                        )
                    )
            token = resp.get("NextPageToken")
            if not token:
                break
        return results

    async def get_resources(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_resources_sync)

    def _get_resources_sync(self) -> list[dict[str, Any]]:
        ec2 = self._client("ec2", self.region)
        resources: list[dict[str, Any]] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"MaxResults": 100}
            if token:
                kwargs["NextToken"] = token
            resp = ec2.describe_instances(**kwargs)
            for reservation in resp.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    instance_id = inst.get("InstanceId", "")
                    name = ""
                    tags = normalize_tags(inst.get("Tags") or [])
                    name = tags.get("name", instance_id)
                    resources.append(
                        {
                            "resource_id": instance_id,
                            "resource_type": "ec2:instance",
                            "name": name,
                            "region": inst.get("Placement", {}).get("AvailabilityZone", self.region),
                            "tags": tags,
                            "metadata": {"state": inst.get("State", {}).get("Name")},
                        }
                    )
            token = resp.get("NextToken")
            if not token:
                break
        return resources

    async def get_commitments(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_commitments_sync)

    def _get_commitments_sync(self) -> list[dict[str, Any]]:
        ce = self._client("ce", "us-east-1")
        commitments: list[dict[str, Any]] = []
        try:
            today = datetime.now(tz=UTC).date()
            util = ce.get_reservation_utilization(
                TimePeriod={
                    "Start": (today - timedelta(days=30)).isoformat(),
                    "End": today.isoformat(),
                },
                Granularity="MONTHLY",
            )
            for items in util.get("UtilizationsByTime", [{}])[0].get("Groups", {}).values():
                for item in items if isinstance(items, list) else []:
                    commitments.append(
                        {
                            "commitment_type": "reserved_instance",
                            "resource_type": item.get("InstanceType"),
                            "arn_or_id": item.get("LeaseId", ""),
                            "utilization_pct": float(item.get("UtilizationPercentage", 0) or 0),
                            "coverage_pct": None,
                            "status": "active",
                        }
                    )
        except Exception as exc:
            logger.info("aws_commitments_partial", error=str(exc))
        return commitments

    def credentials_fingerprint(self) -> str:
        return json.dumps(
            {"role_arn": self.role_arn, "external_id": self.external_id, "region": self.region},
            sort_keys=True,
        )
