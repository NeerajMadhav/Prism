"""Authentication routes: signup, login, tokens, profile, OAuth."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from jose import jwk
from jose import jwt as jose_jwt
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.config.settings import get_settings
from src.middleware.auth import get_current_user
from src.middleware.rate_limit import limiter
from src.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    VerifyEmailRequest,
)
from src.services.email_service import EmailService
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.kv_store import kv_pop, kv_set
from src.utils.logger import get_logger
from src.utils.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])
logger = get_logger(__name__)
email_service = EmailService()


async def _issue_tokens(
    db: asyncpg.Connection,
    user_id: UUID,
    org_id: UUID,
    role: str,
    email: str,
) -> dict[str, str]:
    access = create_access_token(user_id, org_id, role, email)
    raw_refresh = generate_token(64)
    settings = get_settings()
    expires_at = datetime.now(tz=UTC) + timedelta(days=settings.jwt_refresh_expiry_days)
    await db.execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES ($1, $2, $3)
        """,
        user_id,
        hash_token(raw_refresh),
        expires_at,
    )
    return {"access_token": access, "refresh_token": raw_refresh}


@router.post("/signup", response_model=dict)
@limiter.limit("10/15minutes")
async def signup(request: Request, body: SignupRequest, db: asyncpg.Connection = Depends(get_db)) -> dict:
    existing = await db.fetchval("SELECT id FROM users WHERE email = $1", body.email)
    if existing:
        raise AppError("Email already registered", status_code=409, code="conflict")

    password_hash = hash_password(body.password)
    raw_token = generate_token(32)
    token_hash = hash_password(raw_token)
    expires = datetime.now(tz=UTC) + timedelta(hours=24)

    try:
        async with db.transaction():
            user = await db.fetchrow(
                """
                INSERT INTO users (email, name, password_hash, email_verify_token, email_verify_expires)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                body.email,
                body.name,
                password_hash,
                token_hash,
                expires,
            )
            org = await db.fetchrow(
                "INSERT INTO organizations (name) VALUES ($1) RETURNING id",
                body.org_name,
            )
            await db.execute(
                """
                INSERT INTO team_members (org_id, user_id, role, invite_accepted)
                VALUES ($1, $2, 'owner', TRUE)
                """,
                org["id"],
                user["id"],
            )
            await db.execute(
                """
                INSERT INTO notification_settings (org_id, alert_emails)
                VALUES ($1, $2)
                """,
                org["id"],
                [body.email],
            )
    except asyncpg.UniqueViolationError as exc:
        raise AppError("Email already registered", status_code=409, code="conflict") from exc

    email_service.send_verification(body.email, str(user["id"]), raw_token)
    logger.info(
        "user_signup",
        user_id=str(user["id"]),
        org_id=str(org["id"]),
        email=body.email,
    )
    return {
        "message": "Account created. Check your email to verify.",
        "user_id": str(user["id"]),
        "org_id": str(org["id"]),
    }


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("10/15minutes")
async def verify_email(
    request: Request, body: VerifyEmailRequest, db: asyncpg.Connection = Depends(get_db)
) -> MessageResponse:
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", UUID(body.user_id))
    if not user or user["email_verified"]:
        raise AppError("Invalid or expired verification token", status_code=400)
    if not user["email_verify_expires"] or user["email_verify_expires"] < datetime.now(tz=UTC):
        raise AppError("Invalid or expired verification token", status_code=400)
    if not verify_password(body.token, user["email_verify_token"]):
        raise AppError("Invalid or expired verification token", status_code=400)

    await db.execute(
        """
        UPDATE users
        SET email_verified = TRUE, email_verify_token = NULL, email_verify_expires = NULL
        WHERE id = $1
        """,
        user["id"],
    )
    return MessageResponse(message="Email verified. You can now log in.")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("10/15minutes")
async def resend_verification(
    request: Request, body: ResendVerificationRequest, db: asyncpg.Connection = Depends(get_db)
) -> MessageResponse:
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", body.email)
    if user and not user["email_verified"]:
        raw_token = generate_token(32)
        await db.execute(
            """
            UPDATE users
            SET email_verify_token = $1, email_verify_expires = $2
            WHERE id = $3
            """,
            hash_password(raw_token),
            datetime.now(tz=UTC) + timedelta(hours=24),
            user["id"],
        )
        email_service.send_verification(body.email, str(user["id"]), raw_token)
    return MessageResponse(message="If that email exists and is unverified, a new link was sent.")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


@router.post("/login")
@limiter.limit("10/15minutes")
async def login(request: Request, body: LoginRequest, db: asyncpg.Connection = Depends(get_db)) -> dict:
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", body.email)
    valid = verify_password(body.password, user["password_hash"] if user else None)
    if not user or not valid:
        logger.warning("login_failed", email=body.email, ip=_client_ip(request), reason="invalid_credentials")
        raise AppError("Invalid email or password", status_code=401, code="unauthorized")
    if not user["email_verified"]:
        logger.warning("login_failed", email=body.email, ip=_client_ip(request), reason="unverified")
        raise AppError("Check your email to verify your account.", status_code=403, code="forbidden")

    membership = await db.fetchrow(
        """
        SELECT org_id, role FROM team_members
        WHERE user_id = $1 AND invite_accepted = TRUE
        ORDER BY created_at ASC LIMIT 1
        """,
        user["id"],
    )
    if not membership:
        logger.warning("login_failed", email=body.email, ip=_client_ip(request), reason="no_membership")
        raise AppError("No organization membership found", status_code=403)

    tokens = await _issue_tokens(
        db, user["id"], membership["org_id"], membership["role"], user["email"]
    )
    await db.execute("UPDATE users SET last_login = NOW() WHERE id = $1", user["id"])
    logger.info(
        "user_login",
        user_id=str(user["id"]),
        org_id=str(membership["org_id"]),
        email=user["email"],
    )
    return {
        **tokens,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "org_id": str(membership["org_id"]),
            "role": membership["role"],
        },
    }


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/15minutes")
async def refresh(request: Request, body: RefreshRequest, db: asyncpg.Connection = Depends(get_db)) -> TokenResponse:
    # Atomic revoke-by-hash: only one concurrent caller wins the row.
    revoked = await db.fetchrow(
        """
        UPDATE refresh_tokens
        SET revoked_at = NOW()
        WHERE token_hash = $1 AND revoked_at IS NULL AND expires_at > NOW()
        RETURNING user_id
        """,
        hash_token(body.refresh_token),
    )
    if revoked is None:
        raise AppError("Invalid or expired refresh token", status_code=401)

    membership = await db.fetchrow(
        """
        SELECT u.email, tm.org_id, tm.role
        FROM users u
        JOIN team_members tm ON tm.user_id = u.id AND tm.invite_accepted = TRUE
        WHERE u.id = $1
        ORDER BY tm.created_at ASC
        LIMIT 1
        """,
        revoked["user_id"],
    )
    if membership is None:
        raise AppError("No organization membership found", status_code=403)

    tokens = await _issue_tokens(
        db, revoked["user_id"], membership["org_id"], membership["role"], membership["email"]
    )
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("10/15minutes")
async def logout(request: Request, body: LogoutRequest, db: asyncpg.Connection = Depends(get_db)) -> MessageResponse:
    await db.execute(
        """
        UPDATE refresh_tokens
        SET revoked_at = NOW()
        WHERE token_hash = $1 AND revoked_at IS NULL AND expires_at > NOW()
        """,
        hash_token(body.refresh_token),
    )
    return MessageResponse(message="Logged out")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("10/15minutes")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: asyncpg.Connection = Depends(get_db),
) -> MessageResponse:
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", body.email)
    if user and user["email_verified"]:
        raw = generate_token(32)
        # Stored in Postgres so password reset works without Redis.
        await db.execute(
            """
            UPDATE users
            SET password_reset_token = $1, password_reset_expires = $2
            WHERE id = $3
            """,
            hash_password(raw),
            datetime.now(tz=UTC) + timedelta(hours=1),
            user["id"],
        )
        email_service.send_password_reset(body.email, str(user["id"]), raw)
    return MessageResponse(message="If that email exists, a reset link was sent.")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("10/15minutes")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: asyncpg.Connection = Depends(get_db),
) -> MessageResponse:
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", UUID(body.user_id))
    if (
        not user
        or not user["password_reset_token"]
        or not user["password_reset_expires"]
        or user["password_reset_expires"] < datetime.now(tz=UTC)
        or not verify_password(body.token, user["password_reset_token"])
    ):
        raise AppError("Invalid or expired reset token", status_code=400)

    await db.execute(
        """
        UPDATE users
        SET password_hash = $1, password_reset_token = NULL, password_reset_expires = NULL
        WHERE id = $2
        """,
        hash_password(body.new_password),
        UUID(body.user_id),
    )
    await db.execute(
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
        UUID(body.user_id),
    )
    return MessageResponse(message="Password updated. Please log in again.")


@router.get("/me")
async def me(
    current_user: UserContext = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", current_user.user_id)
    if not user:
        raise AppError("Authentication required", status_code=401)
    org = await db.fetchrow("SELECT id, name FROM organizations WHERE id = $1", current_user.org_id)
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user["avatar_url"],
        "org_id": str(current_user.org_id),
        "org_name": org["name"] if org else None,
        "role": current_user.role,
        "email_verified": user["email_verified"],
        "last_login": user["last_login"].isoformat() if user["last_login"] else None,
    }


@router.put("/me")
async def update_me(
    body: UpdateProfileRequest,
    current_user: UserContext = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    user = await db.fetchrow(
        """
        UPDATE users
        SET name = COALESCE($1, name), avatar_url = COALESCE($2, avatar_url)
        WHERE id = $3
        RETURNING id, email, name, avatar_url
        """,
        body.name,
        body.avatar_url,
        current_user.user_id,
    )
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user["avatar_url"],
    }


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserContext = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> MessageResponse:
    user = await db.fetchrow("SELECT password_hash FROM users WHERE id = $1", current_user.user_id)
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise AppError("Current password is incorrect", status_code=400)
    await db.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        hash_password(body.new_password),
        current_user.user_id,
    )
    # Root cause: stolen refresh tokens survived password change — revoke all sessions.
    await db.execute(
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
        current_user.user_id,
    )
    return MessageResponse(message="Password changed")


class OAuthExchangeRequest(BaseModel):
    code: str = Field(min_length=16, max_length=128)


async def _verify_google_id_token(id_token: str, client_id: str) -> dict:
    """Verify Google ID token signature, audience, issuer, and email_verified."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        certs_res = await client.get("https://www.googleapis.com/oauth2/v3/certs")
        certs_res.raise_for_status()
        certs = certs_res.json()
    header = jose_jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    key_data = next((k for k in certs.get("keys", []) if k.get("kid") == kid), None)
    if key_data is None:
        raise ValueError("Unknown Google signing key")
    key = jwk.construct(key_data)
    claims = jose_jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=["https://accounts.google.com", "accounts.google.com"],
        options={"verify_at_hash": False},
    )
    if not claims.get("email_verified"):
        raise ValueError("Google email is not verified")
    return claims


@router.get("/google")
async def google_login(db: asyncpg.Connection = Depends(get_db)) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise AppError("Google OAuth is not configured", status_code=500)
    state = generate_token(16)
    await kv_set(f"oauth:state:{state}", "1", 600, db=db)
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: asyncpg.Connection = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_url
    if not settings.google_client_id:
        return RedirectResponse(f"{frontend}/login?error=oauth_failed")

    # CSRF: state must match a one-time entry created in /google (Redis or DB).
    if not state:
        return RedirectResponse(f"{frontend}/login?error=oauth_state")
    stored = await kv_pop(f"oauth:state:{state}", db=db)
    if not stored:
        return RedirectResponse(f"{frontend}/login?error=oauth_state")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_res.raise_for_status()
            id_token = token_res.json().get("id_token")
            if not id_token:
                raise ValueError("missing id_token")
            claims = await _verify_google_id_token(id_token, settings.google_client_id)
            email = str(claims["email"]).lower()
            name = claims.get("name") or email
            google_id = claims["sub"]
            picture = claims.get("picture")
    except Exception:
        logger.exception("google_oauth_failed")
        return RedirectResponse(f"{frontend}/login?error=oauth_failed")

    user = await db.fetchrow(
        "SELECT * FROM users WHERE google_id = $1",
        google_id,
    )
    if user is None:
        user = await db.fetchrow("SELECT * FROM users WHERE email = $1", email)
        if user is not None:
            # Pre-registration takeover: never attach Google to unverified password accounts.
            if not user["email_verified"]:
                return RedirectResponse(f"{frontend}/login?error=email_unverified")
            if user["google_id"] and user["google_id"] != google_id:
                return RedirectResponse(f"{frontend}/login?error=oauth_failed")
            await db.execute(
                "UPDATE users SET google_id = $1, avatar_url = COALESCE($2, avatar_url) WHERE id = $3",
                google_id,
                picture,
                user["id"],
            )

    if user:
        membership = await db.fetchrow(
            """
            SELECT org_id, role FROM team_members
            WHERE user_id = $1 AND invite_accepted = TRUE
            ORDER BY created_at ASC LIMIT 1
            """,
            user["id"],
        )
        if not membership:
            return RedirectResponse(f"{frontend}/login?error=oauth_failed")
        tokens = await _issue_tokens(
            db, user["id"], membership["org_id"], membership["role"], email
        )
    else:
        async with db.transaction():
            user = await db.fetchrow(
                """
                INSERT INTO users (email, name, google_id, avatar_url, email_verified)
                VALUES ($1, $2, $3, $4, TRUE)
                RETURNING id, email
                """,
                email,
                name,
                google_id,
                picture,
            )
            org = await db.fetchrow(
                "INSERT INTO organizations (name) VALUES ($1) RETURNING id",
                f"{name}'s Org",
            )
            await db.execute(
                """
                INSERT INTO team_members (org_id, user_id, role, invite_accepted)
                VALUES ($1, $2, 'owner', TRUE)
                """,
                org["id"],
                user["id"],
            )
            await db.execute(
                "INSERT INTO notification_settings (org_id, alert_emails) VALUES ($1, $2)",
                org["id"],
                [email],
            )
        tokens = await _issue_tokens(db, user["id"], org["id"], "owner", email)

    # Never put tokens in the URL — one-time exchange code only.
    exchange_code = generate_token(24)
    await kv_set(
        f"oauth:code:{exchange_code}",
        f"{tokens['access_token']}|{tokens['refresh_token']}",
        60,
        db=db,
    )
    return RedirectResponse(f"{frontend}/oauth-callback?code={exchange_code}")


async def _verify_microsoft_id_token(id_token: str, client_id: str, tenant_id: str) -> dict:
    """Verify Microsoft Entra ID token signature, audience, and issuer."""
    # Use common JWKS; issuer is validated against tenant or multi-tenant pattern.
    jwks_url = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
    async with httpx.AsyncClient(timeout=10.0) as client:
        certs_res = await client.get(jwks_url)
        certs_res.raise_for_status()
        certs = certs_res.json()
    header = jose_jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    key_data = next((k for k in certs.get("keys", []) if k.get("kid") == kid), None)
    if key_data is None:
        raise ValueError("Unknown Microsoft signing key")
    key = jwk.construct(key_data)
    claims = jose_jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=client_id,
        options={"verify_iss": False, "verify_at_hash": False},
    )
    iss = str(claims.get("iss", ""))
    allowed_issuers = {
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
        "https://login.microsoftonline.com/common/v2.0",
        "https://login.microsoftonline.com/organizations/v2.0",
    }
    if (
        tenant_id not in ("common", "organizations", "consumers")
        and iss not in allowed_issuers
        and f"/{tenant_id}/" not in iss
    ):
        raise ValueError("Unexpected Microsoft token issuer")
    email = claims.get("email") or claims.get("preferred_username")
    if not email:
        raise ValueError("Microsoft token missing email")
    claims["email"] = str(email).lower()
    claims["sub"] = str(claims.get("oid") or claims.get("sub"))
    return claims


async def _finish_oauth_login(
    db: asyncpg.Connection,
    *,
    email: str,
    name: str,
    provider_user_id: str,
    provider_column: str,
    picture: str | None,
    frontend: str,
) -> RedirectResponse:
    """Shared Google/Microsoft login-or-signup completion."""
    if provider_column not in ("google_id", "microsoft_id"):
        raise ValueError("unsupported oauth provider column")
    user = await db.fetchrow(
        f"SELECT * FROM users WHERE {provider_column} = $1",
        provider_user_id,
    )
    if user is None:
        user = await db.fetchrow("SELECT * FROM users WHERE email = $1", email)
        if user is not None:
            if not user["email_verified"]:
                return RedirectResponse(f"{frontend}/login?error=email_unverified")
            existing = user[provider_column]
            if existing and existing != provider_user_id:
                return RedirectResponse(f"{frontend}/login?error=oauth_failed")
            await db.execute(
                f"UPDATE users SET {provider_column} = $1, avatar_url = COALESCE($2, avatar_url) WHERE id = $3",
                provider_user_id,
                picture,
                user["id"],
            )

    if user:
        membership = await db.fetchrow(
            """
            SELECT org_id, role FROM team_members
            WHERE user_id = $1 AND invite_accepted = TRUE
            ORDER BY created_at ASC LIMIT 1
            """,
            user["id"],
        )
        if not membership:
            return RedirectResponse(f"{frontend}/login?error=oauth_failed")
        tokens = await _issue_tokens(
            db, user["id"], membership["org_id"], membership["role"], email
        )
    else:
        async with db.transaction():
            user = await db.fetchrow(
                f"""
                INSERT INTO users (email, name, {provider_column}, avatar_url, email_verified)
                VALUES ($1, $2, $3, $4, TRUE)
                RETURNING id, email
                """,
                email,
                name,
                provider_user_id,
                picture,
            )
            org = await db.fetchrow(
                "INSERT INTO organizations (name) VALUES ($1) RETURNING id",
                f"{name}'s Org",
            )
            await db.execute(
                """
                INSERT INTO team_members (org_id, user_id, role, invite_accepted)
                VALUES ($1, $2, 'owner', TRUE)
                """,
                org["id"],
                user["id"],
            )
            await db.execute(
                "INSERT INTO notification_settings (org_id, alert_emails) VALUES ($1, $2)",
                org["id"],
                [email],
            )
        tokens = await _issue_tokens(db, user["id"], org["id"], "owner", email)

    exchange_code = generate_token(24)
    await kv_set(
        f"oauth:code:{exchange_code}",
        f"{tokens['access_token']}|{tokens['refresh_token']}",
        60,
        db=db,
    )
    return RedirectResponse(f"{frontend}/oauth-callback?code={exchange_code}")


def _microsoft_redirect_uri() -> str:
    settings = get_settings()
    if settings.microsoft_redirect_uri:
        return settings.microsoft_redirect_uri
    if settings.google_redirect_uri:
        return settings.google_redirect_uri.replace("/google/callback", "/microsoft/callback")
    return "http://127.0.0.1:8000/v1/auth/microsoft/callback"


@router.get("/microsoft")
async def microsoft_login(db: asyncpg.Connection = Depends(get_db)) -> RedirectResponse:
    settings = get_settings()
    if not settings.microsoft_client_id:
        raise AppError("Microsoft OAuth is not configured", status_code=500)
    state = generate_token(16)
    await kv_set(f"oauth:state:{state}", "1", 600, db=db)
    tenant = settings.microsoft_tenant_id or "common"
    redirect_uri = _microsoft_redirect_uri()
    url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
        f"?client_id={settings.microsoft_client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&response_mode=query"
        "&scope=openid%20email%20profile%20offline_access"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: asyncpg.Connection = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_url
    if not settings.microsoft_client_id:
        return RedirectResponse(f"{frontend}/login?error=oauth_failed")
    if not state:
        return RedirectResponse(f"{frontend}/login?error=oauth_state")
    stored = await kv_pop(f"oauth:state:{state}", db=db)
    if not stored:
        return RedirectResponse(f"{frontend}/login?error=oauth_state")

    tenant = settings.microsoft_tenant_id or "common"
    redirect_uri = _microsoft_redirect_uri()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": settings.microsoft_client_id,
                    "client_secret": settings.microsoft_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_res.raise_for_status()
            id_token = token_res.json().get("id_token")
            if not id_token:
                raise ValueError("missing id_token")
            claims = await _verify_microsoft_id_token(
                id_token, settings.microsoft_client_id, tenant
            )
            email = str(claims["email"]).lower()
            name = claims.get("name") or email
            microsoft_id = str(claims["sub"])
            picture = claims.get("picture")
    except Exception:
        logger.exception("microsoft_oauth_failed")
        return RedirectResponse(f"{frontend}/login?error=oauth_failed")

    return await _finish_oauth_login(
        db,
        email=email,
        name=name,
        provider_user_id=microsoft_id,
        provider_column="microsoft_id",
        picture=picture,
        frontend=frontend,
    )


@router.post("/oauth/exchange", response_model=TokenResponse)
@limiter.limit("20/15minutes")
async def oauth_exchange(
    request: Request,
    body: OAuthExchangeRequest,
    db: asyncpg.Connection = Depends(get_db),
) -> TokenResponse:
    """Exchange one-time OAuth code for access/refresh tokens (no tokens in browser URL)."""
    raw = await kv_pop(f"oauth:code:{body.code}", db=db)
    if not raw or "|" not in raw:
        raise AppError("Invalid or expired OAuth code", status_code=401, code="unauthorized")
    access, refresh = raw.split("|", 1)
    return TokenResponse(access_token=access, refresh_token=refresh)
