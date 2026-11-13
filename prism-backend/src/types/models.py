"""Shared dataclasses used across routers and services."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


@dataclass
class UserContext:
    """Authenticated user extracted from JWT."""

    user_id: UUID
    org_id: UUID
    role: str
    email: str
    scopes: list[str] = field(default_factory=list)
    is_api_key: bool = False


@dataclass
class ConnectorResult:
    """Normalized cost row from a cloud connector."""

    time: Any
    service: str
    region: str
    cost_usd: float
    cost_unblended_usd: float
    cost_amortized_usd: float
    usage_quantity: float | None = None
    usage_unit: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    is_estimate: bool = False


@dataclass
class HealthCheckResult:
    """Connector health check outcome."""

    ok: bool
    error: str | None = None


@dataclass
class WSEvent:
    """WebSocket event envelope."""

    event: str
    org_id: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)
