"""Request ID + access-log middleware smoke tests."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://prism:prism@localhost:5432/prism")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("JWT_ACCESS_SECRET", "x" * 32)
os.environ.setdefault("JWT_REFRESH_SECRET", "y" * 32)
os.environ.setdefault(
    "ENCRYPTION_KEY",
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.request_logging import RequestLoggingMiddleware
from src.services.email_service import EmailService


def test_request_id_echoed_and_generated() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "1"}

    client = TestClient(app)
    r1 = client.get("/ping")
    assert r1.status_code == 200
    assert r1.headers.get("X-Request-Id")

    r2 = client.get("/ping", headers={"X-Request-Id": "client-trace-1"})
    assert r2.headers.get("X-Request-Id") == "client-trace-1"


def test_email_send_returns_false_without_ses() -> None:
    svc = EmailService()
    svc._client = None
    assert svc.send_alert_email(["a@example.com"], "Org", "AWS", 90.0, "msg") is False
