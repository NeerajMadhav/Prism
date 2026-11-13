"""Slack interactive callback routes."""

import json
from urllib.parse import parse_qs

import asyncpg
from fastapi import APIRouter, Depends, Response

from src.config.database import get_db
from src.middleware.hmac import validate_hmac
from src.utils.date_utils import utc_now
from src.utils.errors import AppError

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


@router.post("/slack")
async def slack_callback(
    body: bytes = Depends(validate_hmac("slack")),
    db: asyncpg.Connection = Depends(get_db),
) -> Response:
    form = parse_qs(body.decode("utf-8"))
    payload_raw = form.get("payload", [""])[0]
    if not payload_raw:
        return Response(status_code=200)
    payload = json.loads(payload_raw)
    actions = payload.get("actions") or []
    if not actions:
        return Response(status_code=200)
    action = actions[0]
    action_id = action.get("action_id", "")
    alert_id = action.get("value")
    if action_id == "acknowledge_alert" and alert_id:
        await db.execute(
            "UPDATE alerts SET acknowledged_at = $2 WHERE id = $1::uuid",
            alert_id,
            utc_now(),
        )
    elif action_id == "snooze_alert" and alert_id:
        snooze_until = payload.get("state", {}).get("values", {}).get("snooze", {}).get(
            "snooze_input", {}
        ).get("selected_date_time")
        if not snooze_until:
            raise AppError("snooze_until required", status_code=400)
        await db.execute(
            "UPDATE alerts SET snoozed_until = $2::timestamptz WHERE id = $1::uuid",
            alert_id,
            snooze_until,
        )
    return Response(status_code=200)
