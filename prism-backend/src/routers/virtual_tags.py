"""Virtual tag rule routes."""

import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.middleware.org_scope import get_org_access
from src.middleware.rbac import require_role
from src.types.models import UserContext
from src.utils.errors import AppError
from src.utils.regex_utils import validate_regex_pattern
from src.workers.virtual_tags_worker import apply_virtual_tags

router = APIRouter(prefix="/v1/orgs/{org_id}/virtual-tags", tags=["virtual-tags"])


class VirtualTagRuleCreate(BaseModel):
    name: str
    tag_key: str
    tag_value: str
    conditions: list[dict]
    split_config: dict | None = None
    priority: int | None = None


class VirtualTagRuleUpdate(BaseModel):
    name: str | None = None
    tag_key: str | None = None
    tag_value: str | None = None
    conditions: list[dict] | None = None
    split_config: dict | None = None
    is_active: bool | None = None


class ReorderRequest(BaseModel):
    order: list[dict] = Field(min_length=1)


def _validate_conditions(conditions: list[dict]) -> None:
    if not conditions:
        raise AppError("conditions must be non-empty", status_code=400)
    for cond in conditions:
        op = cond.get("op") or cond.get("operator")
        if op == "regex":
            validate_regex_pattern(str(cond.get("value", "")))


def _validate_split(split_config: dict | None) -> None:
    if not split_config:
        return
    targets = split_config.get("targets") or []
    total = sum(float(t.get("pct", 0)) for t in targets)
    if abs(total - 100.0) > 0.01:
        raise AppError("split_config targets must sum to 100", status_code=400)


@router.get("/")
async def list_rules(
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT * FROM virtual_tag_rules
        WHERE org_id = $1
        ORDER BY priority ASC
        """,
        org["id"],
    )
    return [_serialize(r) for r in rows]


@router.post("/", status_code=201)
async def create_rule(
    body: VirtualTagRuleCreate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    _validate_conditions(body.conditions)
    _validate_split(body.split_config)
    priority = body.priority
    if priority is None:
        priority = await db.fetchval(
            "SELECT COALESCE(MAX(priority), 0) + 1 FROM virtual_tag_rules WHERE org_id = $1",
            org["id"],
        )
    row = await db.fetchrow(
        """
        INSERT INTO virtual_tag_rules (
          org_id, name, tag_key, tag_value, conditions, split_config, priority
        ) VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7)
        RETURNING *
        """,
        org["id"],
        body.name,
        body.tag_key,
        body.tag_value,
        json.dumps(body.conditions),
        json.dumps(body.split_config) if body.split_config else None,
        priority,
    )
    return _serialize(row)  # type: ignore[arg-type]


@router.put("/{rule_id}")
async def update_rule(
    rule_id: UUID,
    body: VirtualTagRuleUpdate,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    if body.conditions is not None:
        _validate_conditions(body.conditions)
    if body.split_config is not None:
        _validate_split(body.split_config)
    row = await db.fetchrow(
        """
        UPDATE virtual_tag_rules
        SET name = COALESCE($3, name),
            tag_key = COALESCE($4, tag_key),
            tag_value = COALESCE($5, tag_value),
            conditions = COALESCE($6::jsonb, conditions),
            split_config = COALESCE($7::jsonb, split_config),
            is_active = COALESCE($8, is_active),
            updated_at = NOW()
        WHERE id = $1 AND org_id = $2
        RETURNING *
        """,
        rule_id,
        org["id"],
        body.name,
        body.tag_key,
        body.tag_value,
        json.dumps(body.conditions) if body.conditions is not None else None,
        json.dumps(body.split_config) if body.split_config is not None else None,
        body.is_active,
    )
    if row is None:
        raise AppError("Rule not found", status_code=404)
    return _serialize(row)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    await db.execute(
        "UPDATE virtual_tag_rules SET is_active = FALSE WHERE id = $1 AND org_id = $2",
        rule_id,
        org["id"],
    )
    return {"message": "Rule deactivated"}


@router.put("/reorder")
async def reorder_rules(
    body: ReorderRequest,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    async with db.transaction():
        for item in body.order:
            await db.execute(
                """
                UPDATE virtual_tag_rules SET priority = $3
                WHERE id = $1::uuid AND org_id = $2
                """,
                item["rule_id"],
                org["id"],
                int(item["priority"]),
            )
    return {"message": "Priorities updated"}


@router.post("/{rule_id}/apply")
async def apply_rule(
    rule_id: UUID,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("editor")),
) -> dict:
    task = apply_virtual_tags.apply_async(
        kwargs={"org_id": str(org["id"]), "rule_id": str(rule_id)},
    )
    return {"message": "Retroactive apply started", "task_id": task.id}


@router.get("/audit-log")
async def audit_log(
    request: Request,
    org: dict = Depends(get_org_access),
    _: UserContext = Depends(require_role("viewer")),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    from src.utils.pagination import get_pagination

    params = get_pagination(request)
    rows = await db.fetch(
        """
        SELECT * FROM virtual_tag_audit_log
        WHERE org_id = $1
        ORDER BY started_at DESC
        LIMIT $2 OFFSET $3
        """,
        org["id"],
        params["limit"],
        params["offset"],
    )
    return [
        {
            "id": str(r["id"]),
            "rule_id": str(r["rule_id"]) if r["rule_id"] else None,
            "status": r["status"],
            "started_at": r["started_at"].isoformat(),
            "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
            "rows_processed": r["rows_processed"],
            "rows_updated": r["rows_updated"],
        }
        for r in rows
    ]


def _serialize(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "tag_key": row["tag_key"],
        "tag_value": row["tag_value"],
        "conditions": row["conditions"],
        "split_config": row["split_config"],
        "priority": row["priority"],
        "is_active": row["is_active"],
    }
