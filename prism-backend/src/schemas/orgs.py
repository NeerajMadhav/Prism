"""Organization request/response schemas."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class OrgResponse(BaseModel):
    id: str
    name: str
    plan: str
    billing_period_start: date | None
    currency: str
    timezone: str
    feature_flags: dict[str, Any]
    created_at: str


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    billing_period_start: date | None = None
