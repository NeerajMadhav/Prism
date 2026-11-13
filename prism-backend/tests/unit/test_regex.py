"""Unit tests for ReDoS-safe regex validation."""

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
from src.utils.regex_utils import safe_regex_test, validate_regex_pattern


def test_safe_pattern_ok() -> None:
    validate_regex_pattern(r"^prod-.*$")
    assert safe_regex_test(r"^prod-.*$")


def test_invalid_pattern_rejected() -> None:
    with pytest.raises(AppError):
        validate_regex_pattern(r"[unterminated")


def test_pattern_too_long_rejected() -> None:
    with pytest.raises(AppError):
        validate_regex_pattern("a" * 201)
