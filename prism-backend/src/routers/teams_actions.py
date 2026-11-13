"""Microsoft Teams interactive callback routes."""

import json

import asyncpg
from fastapi import APIRouter, Depends, Response

from src.config.database import get_db
from src.middleware.hmac import validate_hmac
from src.utils.date_utils import utc_now
from src.utils.errors import AppError

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


@router.post("/teams")
async def teams_callback(
    body: bytes = Depends(validate_hmac("teams")),
    db: asyncpg.Connection = Depends(get_db),
) -> Response:
    payload = json.loads(body.decode("utf-8"))
    value = payload.get("value") or {}
    action = value.get("action", {})
    action_type = action.get("type") or value.get("type")
    alert_id = value.get("alert_id") or action.get("data", {}).get("alert_id")
    if action_type == "acknowledge" and alert_id:
        await db.execute(
            "UPDATE alerts SET acknowledged_at = $2 WHERE id = $1::uuid",
            alert_id,
            utc_now(),
        )
        return Response(status_code=200)
    if action_type == "snooze" and alert_id:
        snooze_until = value.get("snooze_until") or action.get("data", {}).get("snooze_until")
        if not snooze_until:
            raise AppError("snooze_until required", status_code=400)
        await db.execute(
            "UPDATE alerts SET snoozed_until = $2::timestamptz WHERE id = $1::uuid",
            alert_id,
            snooze_until,
        )
    return Response(status_code=200)
