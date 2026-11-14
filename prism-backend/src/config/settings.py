"""Load and validate all environment variables. Fail fast if required ones are missing."""

import hashlib
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(alias="DATABASE_URL")
    database_pool_min: int = Field(default=5, alias="DATABASE_POOL_MIN")
    database_pool_max: int = Field(default=20, alias="DATABASE_POOL_MAX")

    # Redis/Celery are optional for core API — degrade when unset or unreachable.
    redis_url: str = Field(default="", alias="REDIS_URL")
    celery_broker_url: str = Field(default="", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="", alias="CELERY_RESULT_BACKEND")

    jwt_access_secret: str = Field(min_length=32, alias="JWT_ACCESS_SECRET")
    jwt_refresh_secret: str = Field(min_length=32, alias="JWT_REFRESH_SECRET")
    # Short-lived access tokens limit blast radius of stolen JWTs / stale roles.
    jwt_access_expiry_minutes: int = Field(default=15, alias="JWT_ACCESS_EXPIRY_MINUTES")
    jwt_refresh_expiry_days: int = Field(default=30, alias="JWT_REFRESH_EXPIRY_DAYS")
    # Dedicated secret for /internal/* — never reuse JWT access secret.
    prism_internal_secret: str = Field(default="", alias="PRISM_INTERNAL_SECRET")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="", alias="GOOGLE_REDIRECT_URI")

    microsoft_client_id: str = Field(default="", alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str = Field(default="", alias="MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id: str = Field(default="common", alias="MICROSOFT_TENANT_ID")
    microsoft_redirect_uri: str = Field(default="", alias="MICROSOFT_REDIRECT_URI")

    ms_graph_tenant_id: str = Field(default="", alias="MS_GRAPH_TENANT_ID")
    ms_graph_client_id: str = Field(default="", alias="MS_GRAPH_CLIENT_ID")
    ms_graph_client_secret: str = Field(default="", alias="MS_GRAPH_CLIENT_SECRET")
    ms_graph_sender: str = Field(default="", alias="MS_GRAPH_SENDER")

    aws_ses_region: str = Field(default="us-east-1", alias="AWS_SES_REGION")
    aws_ses_from: str = Field(default="noreply@prism.io", alias="AWS_SES_FROM")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")

    encryption_key: str = Field(min_length=64, alias="ENCRYPTION_KEY")
    prism_aws_account_id: str = Field(default="", alias="PRISM_AWS_ACCOUNT_ID")

    teams_signing_secret: str = Field(default="", alias="TEAMS_SIGNING_SECRET")
    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")

    frontend_url: str = Field(alias="FRONTEND_URL")
    worker_concurrency: int = Field(default=8, alias="WORKER_CONCURRENCY")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def internal_api_secret(self) -> str:
        """Secret for worker→API internal calls.

        Production requires dedicated PRISM_INTERNAL_SECRET (fail closed).
        Development may derive a local-only fallback from ENCRYPTION_KEY.
        """
        if self.prism_internal_secret:
            return self.prism_internal_secret
        if self.is_production:
            raise RuntimeError(
                "PRISM_INTERNAL_SECRET must be set in production "
                "(do not derive from ENCRYPTION_KEY)"
            )
        return hashlib.sha256(f"prism-internal:{self.encryption_key}".encode()).hexdigest()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
