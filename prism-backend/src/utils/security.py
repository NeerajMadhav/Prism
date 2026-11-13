"""Password hashing and JWT helpers."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dummy hash for timing-safe login when user is missing
_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    """Hash a password with bcrypt cost factor 12."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    """Verify password; use dummy hash if hashed is None (timing safety)."""
    return pwd_context.verify(plain, hashed or _DUMMY_HASH)


def hash_token(raw: str) -> str:
    """SHA-256 hex digest for opaque tokens (refresh, API keys lookup-friendly)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically random hex token."""
    return secrets.token_hex(nbytes)


def create_access_token(
    user_id: UUID | str,
    org_id: UUID | str,
    role: str,
    email: str,
) -> str:
    """Sign a short-lived access JWT."""
    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_access_secret, algorithm="HS256")


def create_refresh_token_jwt(user_id: UUID | str) -> str:
    """Sign a long-lived refresh JWT (raw secret stored hashed separately)."""
    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expiry_days),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_access_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise ValueError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token JWT."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_refresh_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid or expired refresh token") from exc
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")
    return payload
