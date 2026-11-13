"""Team management schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.schemas.auth import _validate_password


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    name: str
    role: str
    invite_accepted: bool
    created_at: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: EmailStr) -> str:
        return str(v).lower()

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("admin", "editor", "viewer"):
            raise ValueError("role must be admin, editor, or viewer")
        return v


class AcceptInviteRequest(BaseModel):
    token: str
    org_id: str
    name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password(v)


class ChangeRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("owner", "admin", "editor", "viewer"):
            raise ValueError("invalid role")
        return v


class InviteCreatedResponse(BaseModel):
    message: str
    invite_id: str


class MessageResponse(BaseModel):
    message: str
