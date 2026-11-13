"""Alert schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: str
    type: str
    scope: str | None
    scope_value: str | None
    severity: str
    threshold_percent: float | None
    message: str
    triggered_at: str
    acknowledged_at: str | None
    acknowledged_by: str | None
    snoozed_until: str | None
    cap_id: str | None


class SnoozeRequest(BaseModel):
    snooze_until: datetime = Field(description="ISO-8601 datetime until which alert is snoozed")


class MessageResponse(BaseModel):
    message: str
