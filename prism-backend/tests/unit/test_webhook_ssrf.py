"""Unit tests for SSRF webhook URL validation."""

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

import pytest

from src.utils.errors import AppError
from src.utils.validate_webhook_url import validate_webhook_url, verify_dispatch_url


def test_rejects_http() -> None:
    with pytest.raises(AppError):
        validate_webhook_url("http://example.com/hook")


def test_rejects_localhost() -> None:
    with pytest.raises(AppError):
        validate_webhook_url("https://127.0.0.1/hook")


def test_rejects_file_scheme() -> None:
    with pytest.raises(AppError):
        validate_webhook_url("file:///etc/passwd")


def test_verify_dispatch_false_for_private() -> None:
    assert verify_dispatch_url("https://127.0.0.1/x") is False
