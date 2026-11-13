"""WebSocket manager: JWT auth, per-org connection registry, broadcast."""

import asyncio
import base64
import binascii
import hmac
import json
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Header, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from src.config.database import get_pool
from src.config.settings import get_settings
from src.utils.date_utils import utc_now
from src.utils.errors import AppError
from src.utils.logger import get_logger
from src.utils.security import decode_access_token

logger = get_logger(__name__)

# ponytail: in-memory only; upgrade to Redis Pub/Sub for multi-instance
org_connections: dict[str, set[WebSocket]] = {}

router = APIRouter(tags=["websocket"])

_WS_PROTO_PREFIX = "prism.jwt."


def _event_envelope(event: str, org_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "event": event,
        "org_id": org_id,
        "timestamp": utc_now().isoformat(),
        "data": data,
    }


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _extract_token_from_protocols(header: str) -> tuple[str | None, str | None]:
    """Return (token, chosen_subprotocol) from Sec-WebSocket-Protocol."""
    for part in header.split(","):
        proto = part.strip()
        if not proto.startswith(_WS_PROTO_PREFIX):
            continue
        encoded = proto[len(_WS_PROTO_PREFIX) :]
        try:
            token = _b64url_decode(encoded).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return None, None
        return token, proto
    return None, None


async def _ping_loop(ws: WebSocket, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=30.0)
            return
        except TimeoutError:
            if ws.client_state != WebSocketState.CONNECTED:
                return
            try:
                await ws.send_json({"event": "ping", "timestamp": utc_now().isoformat()})
            except Exception:
                return


async def ws_broadcast(org_id: str, event_dict: dict[str, Any]) -> None:
    """Send an event to all connected clients for an org."""
    targets = list(org_connections.get(org_id, set()))
    if not targets:
        return
    payload = json.dumps(event_dict)
    dead: list[WebSocket] = []
    for ws in targets:
        if ws.client_state != WebSocketState.CONNECTED:
            dead.append(ws)
            continue
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    if dead:
        org_connections.setdefault(org_id, set()).difference_update(dead)
        if not org_connections.get(org_id):
            org_connections.pop(org_id, None)


def worker_ws_broadcast(org_id: str, event: str, data: dict[str, Any]) -> None:
    """POST broadcast to API process from Celery workers."""
    settings = get_settings()
    import os

    api_base = os.environ.get("API_INTERNAL_URL", f"http://127.0.0.1:{settings.port}")
    envelope = _event_envelope(event, org_id, data)
    try:
        httpx.post(
            f"{api_base}/internal/ws-broadcast",
            json=envelope,
            headers={"X-Prism-Internal": settings.internal_api_secret},
            timeout=5.0,
        )
    except Exception as exc:
        logger.warning("worker_ws_broadcast_failed", org_id=org_id, error=str(exc))


async def _verify_membership(user_id: str, org_id: str) -> bool:
    """Match HTTP auth: removed/demoted users must not keep a WS session."""
    pool = get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            """
            SELECT 1
            FROM team_members
            WHERE user_id = $1 AND org_id = $2 AND invite_accepted = TRUE
            """,
            UUID(user_id),
            UUID(org_id),
        )
    return row is not None


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Authenticate via Sec-WebSocket-Protocol (never query-string JWT)."""
    header = ws.headers.get("sec-websocket-protocol", "")
    token, subprotocol = _extract_token_from_protocols(header)
    if not token or not subprotocol:
        await ws.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_access_token(token)
    except ValueError:
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    org_id = str(payload["org_id"])
    user_id = str(payload["sub"])
    try:
        ok = await _verify_membership(user_id, org_id)
    except Exception as exc:
        logger.warning("ws_membership_check_failed", error=str(exc))
        await ws.close(code=1011, reason="Auth check failed")
        return
    if not ok:
        await ws.close(code=4003, reason="Not a member of this organization")
        return

    await ws.accept(subprotocol=subprotocol)
    org_connections.setdefault(org_id, set()).add(ws)
    logger.info(
        "ws_connected",
        org_id=org_id,
        user_id=user_id,
        connections=len(org_connections.get(org_id, set())),
    )
    stop = asyncio.Event()
    ping_task = asyncio.create_task(_ping_loop(ws, stop))
    try:
        await ws.send_json(_event_envelope("connected", org_id, {}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        stop.set()
        ping_task.cancel()
        org_connections.get(org_id, set()).discard(ws)
        if org_id in org_connections and not org_connections[org_id]:
            org_connections.pop(org_id, None)
        logger.info(
            "ws_disconnected",
            org_id=org_id,
            user_id=user_id,
            connections=len(org_connections.get(org_id, set())),
        )


@router.post("/internal/ws-broadcast")
async def internal_ws_broadcast(
    body: dict[str, Any],
    x_prism_internal: str | None = Header(default=None, alias="X-Prism-Internal"),
) -> dict[str, str]:
    settings = get_settings()
    expected = settings.internal_api_secret
    if not expected:
        raise AppError("Internal API disabled", status_code=503)
    if not x_prism_internal or not hmac_compare(x_prism_internal, expected):
        raise AppError("Forbidden", status_code=403)
    org_id = str(body.get("org_id", ""))
    if not org_id:
        raise AppError("org_id required", status_code=400)
    await ws_broadcast(org_id, body)
    return {"status": "ok"}


def hmac_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
