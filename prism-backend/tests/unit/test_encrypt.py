"""Unit tests for AES encrypt/decrypt."""

import os

import pytest

# Ensure settings can load before importing encrypt
os.environ.setdefault(
    "DATABASE_URL", "postgresql://prism:prism@localhost:5432/prism"
)
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

from cryptography.exceptions import InvalidTag

from src.config.settings import get_settings
from src.utils.encrypt import aes_decrypt, aes_encrypt


def test_encrypt_decrypt_roundtrip() -> None:
    get_settings.cache_clear()
    plain = '{"role_arn":"arn:aws:iam::123:role/Prism"}'
    token = aes_encrypt(plain)
    assert aes_decrypt(token) == plain


def test_wrong_key_raises() -> None:
    get_settings.cache_clear()
    token = aes_encrypt("secret")
    get_settings.cache_clear()
    os.environ["ENCRYPTION_KEY"] = "ff" * 32
    get_settings.cache_clear()
    with pytest.raises(InvalidTag):
        aes_decrypt(token)
    # restore
    os.environ["ENCRYPTION_KEY"] = (
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    get_settings.cache_clear()
