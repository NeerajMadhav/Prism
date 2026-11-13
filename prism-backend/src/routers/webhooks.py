"""Outbound webhook configuration routes."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.services.webhook_service import OutboundWebhookService
from src.types.models import UserContext
from src.utils.encrypt import aes_encrypt
from src.utils.errors import AppError
from src.utils.security import generate_token
from src.utils.validate_webhook_url import validate_webhook_url

router = APIRouter(prefix="/v1/orgs/{org_id}/webhooks", tags=["webhooks"])
ALLOWED_EVENTS = {"alert.fired", "sync.complete", "forecast.updated", "report.sent"}


class WebhookCreate(BaseModel):
    url: str
    events: list[str] = Field(min_length=1)


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


@router.get("/")
async def list_webhooks(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        "SELECT id, url, events, is_active, last_delivery_status, last_delivery_at, created_at FROM outbound_webhooks WHERE org_id = $1",
        org["id"],
    )
    return [
        {
            "id": str(r["id"]),
            "url": r["url"],
            "events": r["events"],
            "is_active": r["is_active"],
            "last_delivery_status": r["last_delivery_status"],
            "last_delivery_at": r["last_delivery_at"].isoformat() if r["last_delivery_at"] else None,
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.post("/", status_code=201)
async def create_webhook(
    body: WebhookCreate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    validate_webhook_url(body.url)
    invalid = set(body.events) - ALLOWED_EVENTS
    if invalid:
        raise AppError(f"Invalid events: {', '.join(sorted(invalid))}", status_code=400)
    signing_secret = generate_token(32)
    row = await db.fetchrow(
        """
        INSERT INTO outbound_webhooks (org_id, url, signing_secret_enc, events)
        VALUES ($1, $2, $3, $4)
        RETURNING id, url, events, created_at
        """,
        org["id"],
        body.url,
        aes_encrypt(signing_secret),
        body.events,
    )
    return {
        "id": str(row["id"]),
        "url": row["url"],
        "events": row["events"],
        "signing_secret": signing_secret,
    }


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    if body.url:
        validate_webhook_url(body.url)
    if body.events:
        invalid = set(body.events) - ALLOWED_EVENTS
        if invalid:
            raise AppError(f"Invalid events: {', '.join(sorted(invalid))}", status_code=400)
    row = await db.fetchrow(
        """
        UPDATE outbound_webhooks
        SET url = COALESCE($3, url),
            events = COALESCE($4, events),
            is_active = COALESCE($5, is_active)
        WHERE id = $1 AND org_id = $2
        RETURNING id, url, events, is_active
        """,
        webhook_id,
        org["id"],
        body.url,
        body.events,
        body.is_active,
    )
    if row is None:
        raise AppError("Webhook not found", status_code=404)
    return {"id": str(row["id"]), "url": row["url"], "events": row["events"], "is_active": row["is_active"]}


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute("DELETE FROM outbound_webhooks WHERE id = $1 AND org_id = $2", webhook_id, org["id"])
    return {"message": "Webhook deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    row = await db.fetchrow(
        "SELECT url, signing_secret_enc FROM outbound_webhooks WHERE id = $1 AND org_id = $2 AND is_active = TRUE",
        webhook_id,
        org["id"],
    )
    if row is None:
        raise AppError("Webhook not found", status_code=404)
    service = OutboundWebhookService()
    ok, status_code, error = await service.send_test(
        row["url"],
        row["signing_secret_enc"],
        str(org["id"]),
    )
    return {"ok": ok, "status_code": status_code, "error": error}
