"""Unit tests for password hashing and JWT."""

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

from src.config.settings import get_settings
from src.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_roundtrip() -> None:
    get_settings.cache_clear()
    h = hash_password("Secret1!")
    assert verify_password("Secret1!", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip() -> None:
    get_settings.cache_clear()
    token = create_access_token("u1", "o1", "owner", "a@b.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "u1"
    assert payload["org_id"] == "o1"
    assert payload["role"] == "owner"


def test_hash_token_stable() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
    assert len(hash_token("x")) == 64
