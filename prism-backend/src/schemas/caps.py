"""Budget cap schemas."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CapCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scope: Literal["platform", "service", "account"]
    scope_value: str = Field(min_length=1, max_length=200)
    cap_amount: Decimal = Field(gt=0)
    period: str = "monthly"


class CapUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    cap_amount: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class CapResponse(BaseModel):
    id: str
    name: str
    scope: str
    scope_value: str
    cap_amount: float
    period: str
    is_active: bool
    created_at: str
    updated_at: str
    current_month_spend: float | None = None
    pct_used: float | None = None


class CapDetailResponse(CapResponse):
    alert_history: list[dict[str, object]] = Field(default_factory=list)
