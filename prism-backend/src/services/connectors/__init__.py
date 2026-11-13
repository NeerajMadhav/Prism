"""Cloud provider connectors."""

import json
import re
from typing import Any

from src.services.connectors.aws import AWSConnector
from src.services.connectors.azure import AzureConnector
from src.services.connectors.gcp import GCPConnector
from src.services.connectors.tags import normalize_tags
from src.types.models import ConnectorResult, HealthCheckResult


def extract_aws_account_id(role_arn: str) -> str:
    """Parse 12-digit account id from IAM role ARN."""
    match = re.search(r"arn:aws:iam::(\d{12}):", role_arn)
    if not match:
        raise ValueError("Invalid AWS role ARN")
    return match.group(1)


def get_connector(
    provider: str,
    credentials_json: str,
    cloud_account_id: str,
    fx_rate: float = 1.0,
) -> AWSConnector | AzureConnector | GCPConnector:
    """Instantiate the connector for a provider."""
    creds: dict[str, Any] = json.loads(credentials_json)
    if provider == "aws":
        return AWSConnector(creds, cloud_account_id)
    if provider == "azure":
        return AzureConnector(creds, cloud_account_id, fx_rate=fx_rate)
    if provider == "gcp":
        return GCPConnector(creds, cloud_account_id)
    raise ValueError(f"Unsupported provider: {provider}")


__all__ = [
    "AWSConnector",
    "AzureConnector",
    "ConnectorResult",
    "GCPConnector",
    "HealthCheckResult",
    "extract_aws_account_id",
    "get_connector",
    "normalize_tags",
]
