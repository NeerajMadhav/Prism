"""Team membership and invite routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.schemas.team import (
    AcceptInviteRequest,
    ChangeRoleRequest,
    InviteCreatedResponse,
    InviteRequest,
    MessageResponse,
)
from src.services.email_service import EmailService
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.security import generate_token, hash_password, verify_password

router = APIRouter(prefix="/v1/orgs/{org_id}/team", tags=["team"])
email_service = EmailService()


def _serialize_member(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "invite_accepted": row["invite_accepted"],
        "created_at": row["created_at"].isoformat(),
    }


@router.get("")
async def list_team(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT tm.*, u.email, u.name
        FROM team_members tm
        JOIN users u ON u.id = tm.user_id
        WHERE tm.org_id = $1
        ORDER BY tm.created_at ASC
        """,
        org["id"],
    )
    return [_serialize_member(r) for r in rows]


@router.post("/invite", response_model=InviteCreatedResponse, status_code=201)
async def invite_member(
    body: InviteRequest,
    org: dict = Depends(get_org_access),
    current_user: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> InviteCreatedResponse:
    existing_member = await db.fetchval(
        """
        SELECT 1 FROM team_members tm
        JOIN users u ON u.id = tm.user_id
        WHERE tm.org_id = $1 AND u.email = $2
        """,
        org["id"],
        body.email,
    )
    if existing_member:
        raise AppError("User is already a team member", status_code=409, code="conflict")

    active_invite = await db.fetchval(
        """
        SELECT 1 FROM invites
        WHERE org_id = $1 AND email = $2 AND accepted_at IS NULL AND expires_at > NOW()
        """,
        org["id"],
        body.email,
    )
    if active_invite:
        raise AppError("An active invite already exists for this email", status_code=409)

    raw_token = generate_token(32)
    expires = datetime.now(tz=UTC) + timedelta(days=7)
    invite = await db.fetchrow(
        """
        INSERT INTO invites (org_id, email, role, token_hash, expires_at, invited_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        org["id"],
        body.email,
        body.role,
        hash_password(raw_token),
        expires,
        current_user.user_id,
    )
    email_service.send_invite(body.email, str(org["id"]), org["name"], raw_token, body.role)
    return InviteCreatedResponse(message="Invite sent", invite_id=str(invite["id"]))


@router.post("/accept-invite", response_model=dict)
async def accept_invite(
    body: AcceptInviteRequest,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    org_id = UUID(body.org_id)
    invites = await db.fetch(
        """
        SELECT * FROM invites
        WHERE org_id = $1 AND accepted_at IS NULL
        ORDER BY created_at DESC
        """,
        org_id,
    )
    invite = None
    for row in invites:
        if verify_password(body.token, row["token_hash"]):
            invite = row
            break
    if not invite:
        raise AppError("Invalid invite token", status_code=400)
    if invite["expires_at"] < datetime.now(tz=UTC):
        raise AppError("Invite has expired", status_code=400)

    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", invite["email"])
    async with db.transaction():
        if not user:
            if not body.name or not body.password:
                raise AppError("Name and password required for new users", status_code=400)
            user = await db.fetchrow(
                """
                INSERT INTO users (email, name, password_hash, email_verified)
                VALUES ($1, $2, $3, TRUE)
                RETURNING id
                """,
                invite["email"],
                body.name,
                hash_password(body.password),
            )
        existing = await db.fetchval(
            "SELECT 1 FROM team_members WHERE org_id = $1 AND user_id = $2",
            org_id,
            user["id"],
        )
        if existing:
            raise AppError("User is already a member", status_code=409)
        await db.execute(
            """
            INSERT INTO team_members (org_id, user_id, role, invite_accepted, invited_by)
            VALUES ($1, $2, $3, TRUE, $4)
            """,
            org_id,
            user["id"],
            invite["role"],
            invite["invited_by"],
        )
        await db.execute(
            "UPDATE invites SET accepted_at = NOW() WHERE id = $1",
            invite["id"],
        )
    return {"message": "Invite accepted", "user_id": str(user["id"])}


@router.put("/{member_id}/role")
async def change_role(
    member_id: UUID,
    body: ChangeRoleRequest,
    org: dict = Depends(get_org_access),
    current_user: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    member = await db.fetchrow(
        "SELECT * FROM team_members WHERE id = $1 AND org_id = $2",
        member_id,
        org["id"],
    )
    if not member:
        raise AppError("Member not found", status_code=404)

    if member["role"] == "owner" and body.role != "owner":
        raise AppError("Cannot demote the organization owner", status_code=403)

    if body.role == "owner":
        if current_user.role != "owner":
            raise AppError("Only the owner can assign ownership", status_code=403)
        async with db.transaction():
            await db.execute(
                "UPDATE team_members SET role = 'admin' WHERE org_id = $1 AND role = 'owner'",
                org["id"],
            )
            await db.execute(
                "UPDATE team_members SET role = $1 WHERE id = $2",
                body.role,
                member_id,
            )
    else:
        await db.execute(
            "UPDATE team_members SET role = $1 WHERE id = $2 AND org_id = $3",
            body.role,
            member_id,
            org["id"],
        )

    row = await db.fetchrow(
        """
        SELECT tm.*, u.email, u.name FROM team_members tm
        JOIN users u ON u.id = tm.user_id
        WHERE tm.id = $1
        """,
        member_id,
    )
    return _serialize_member(row)  # type: ignore[arg-type]


@router.delete("/{member_id}", response_model=MessageResponse)
async def remove_member(
    member_id: UUID,
    org: dict = Depends(get_org_access),
    current_user: UserContext = Depends(require_role("admin")),
    db: asyncpg.Connection = Depends(get_db),
) -> MessageResponse:
    member = await db.fetchrow(
        "SELECT * FROM team_members WHERE id = $1 AND org_id = $2",
        member_id,
        org["id"],
    )
    if not member:
        raise AppError("Member not found", status_code=404)
    if member["role"] == "owner":
        raise AppError("Cannot remove the organization owner", status_code=403)
    if member["user_id"] == current_user.user_id and current_user.role == "owner":
        raise AppError("Owner cannot remove themselves", status_code=403)
    await db.execute("DELETE FROM team_members WHERE id = $1", member_id)
    # Drop sessions so removed users cannot refresh into a leftover membership race.
    await db.execute(
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
        member["user_id"],
    )
    return MessageResponse(message="Member removed")
