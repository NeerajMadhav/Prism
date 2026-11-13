"""Cloud account schemas."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AWSCredentials(BaseModel):
    role_arn: str
    external_id: str
    region: str = "us-east-1"


class AzureCredentials(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str


class GCPCredentials(BaseModel):
    project_id: str
    dataset_id: str
    table_prefix: str
    service_account_json: dict[str, Any]


class AccountCreateRequest(BaseModel):
    provider: Literal["aws", "azure", "gcp"]
    display_name: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=200)
    credentials: dict[str, Any]

    @field_validator("credentials")
    @classmethod
    def validate_credentials(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        provider = info.data.get("provider")
        if provider == "aws":
            AWSCredentials.model_validate(v)
        elif provider == "azure":
            AzureCredentials.model_validate(v)
        elif provider == "gcp":
            GCPCredentials.model_validate(v)
        return v


class AccountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    credentials: dict[str, Any] | None = None


class AccountResponse(BaseModel):
    id: str
    provider: str
    account_id: str
    display_name: str
    scope: str
    last_sync: datetime | None
    last_sync_status: str
    last_sync_error: str | None
    data_as_of: date | None
    is_active: bool
    created_at: str


class AccountCreatedResponse(BaseModel):
    id: str
    provider: str
    account_id: str
    display_name: str
    last_sync_status: str
    created_at: str


class HealthCheckResponse(BaseModel):
    ok: bool
    error: str | None = None


class SyncTriggerResponse(BaseModel):
    message: str
    task_id: str


class SyncLogResponse(BaseModel):
    id: str
    status: str
    started_at: str
    finished_at: str | None
    records_synced: int | None
    error: str | None
