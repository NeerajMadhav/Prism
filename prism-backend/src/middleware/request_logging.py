"""Per-request correlation ID + HTTP access logging (Part 22 observability)."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.utils.logger import get_logger

logger = get_logger(__name__)

# High-volume / probe paths — log at debug to keep prod INFO useful.
_QUIET_PATHS = frozenset({"/health", "/favicon.ico"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Bind request_id for the request lifetime; emit http_request after response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        clear_contextvars()
        incoming = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
        request_id = incoming.strip() if incoming else str(uuid.uuid4())
        bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            status = response.status_code if response is not None else 500
            path = request.url.path
            event = {
                "method": request.method,
                "path": path,
                "status": status,
                "duration_ms": duration_ms,
            }
            if path in _QUIET_PATHS:
                logger.debug("http_request", **event)
            else:
                logger.info("http_request", **event)
            if response is not None:
                response.headers["X-Request-Id"] = request_id
            clear_contextvars()
